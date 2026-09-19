"""QLC+ Virtual Console bridge: passive discovery + gated control.

QLC+ (qlcplus.org) exposes a WebSocket API at ws://<host>:9999/qlcplusWS.
Every command/response format below was verified against the QLC+
maintainer's own webaccess/res/Test_Web_API.html (github.com/mcallegari/
qlcplus) -- not the various community forum posts, two of which were
found to disagree with each other and with this authoritative source on
the exact write-command format.

Two distinct command styles exist:
  - "Queries" (read discovery): "QLC+API|<command>[|<param>...]", answered
    with "QLC+API|<command>|<data...>".
  - "High rate" writes (control): no "QLC+API|" prefix at all -- these are
    deliberately minimal to avoid overhead for things like a fast-moving
    slider. E.g. setting a widget's value is just "<widgetId>|<value>".

This module follows this project's supervision/emission split: discovery
(async_update/snapshot) is passive and always safe to run; every write
method requires the caller to have already checked the security gate,
the same convention as every other active-output module here (see
gdtf-panel/power-manager-panel's set_control_enabled/set_*_enabled
pattern) -- this module intentionally does not gate itself, so the
caller (a service handler) is where that check belongs, exactly as with
OSC/MIDI output elsewhere in this project.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

DEFAULT_PORT = 9999
DEFAULT_TIMEOUT = 3.0


@dataclass
class QlcWidget:
    widget_id: str
    name: str
    widget_type: str | None = None
    status: str | None = None


@dataclass
class QlcFunction:
    function_id: str
    name: str
    function_type: str | None = None
    status: str | None = None


@dataclass
class QlcState:
    host: str
    port: int
    online: bool = False
    last_error: str | None = None
    last_poll: float | None = None
    last_success: float | None = None
    widgets: dict[str, QlcWidget] = field(default_factory=dict)
    functions: dict[str, QlcFunction] = field(default_factory=dict)
    last_command: dict[str, Any] | None = None


class QlcPlusBridge:
    """One persistent WebSocket connection to a QLC+ instance."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.host = str(host).strip()
        self.port = int(port)
        self.timeout = max(0.5, min(10.0, float(timeout)))
        self.state = QlcState(self.host, self.port)
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._lock = asyncio.Lock()

    @property
    def _url(self) -> str:
        return f"ws://{self.host}:{self.port}/qlcplusWS"

    async def _ensure_connected(self) -> aiohttp.ClientWebSocketResponse:
        if self._ws is not None and not self._ws.closed:
            return self._ws
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=self.timeout))
        self._ws = await self._session.ws_connect(self._url, timeout=self.timeout)
        return self._ws

    async def _query(self, command: str, *params: str, expect: str | None = None) -> list[str] | None:
        """Send a "QLC+API|command[|params]" query and wait for the
        matching "QLC+API|<expect or command>|..." reply, skipping over
        any unrelated messages that arrive first (QLC+ has no request-ID
        correlation, so this is the same tolerant approach the community
        examples use -- match by response command name, not strict order).
        """
        expect = expect or command
        async with self._lock:  # one request/response pair at a time on this connection
            ws = await self._ensure_connected()
            payload = "QLC+API|" + command + ("|" + "|".join(params) if params else "")
            await ws.send_str(payload)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                remaining = max(0.05, deadline - time.monotonic())
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                parts = msg.data.split("|")
                if len(parts) >= 2 and parts[0] == "QLC+API" and parts[1] == expect:
                    return parts
            return None

    async def async_update(self) -> None:
        """Passive discovery: widget and function inventories. Read-only."""
        self.state.last_poll = time.time()
        try:
            widgets_reply = await self._query("getWidgetsList")
            if widgets_reply is None:
                raise TimeoutError("no response to getWidgetsList")
            widgets: dict[str, QlcWidget] = {}
            for i in range(2, len(widgets_reply) - 1, 2):
                wid, name = widgets_reply[i], widgets_reply[i + 1]
                widgets[wid] = QlcWidget(wid, name)
            for wid, widget in widgets.items():
                type_reply = await self._query("getWidgetType", wid)
                # Per Test_Web_API.html: "QLC+API|getWidgetType|<echoedId>|<type>" -- type is index 3.
                if type_reply and len(type_reply) > 3:
                    widget.widget_type = type_reply[3]
                status_reply = await self._query("getWidgetStatus", wid)
                # Per Test_Web_API.html: status value is always at index 3
                # (index 2 is either 'PLAY' for Cue List widgets, in which
                # case index 3 is the current step, or some other field for
                # other widget types -- never the status itself).
                if status_reply and len(status_reply) > 3:
                    widget.status = status_reply[3]

            functions_reply = await self._query("getFunctionsList")
            functions: dict[str, QlcFunction] = {}
            if functions_reply:
                for i in range(2, len(functions_reply) - 1, 2):
                    fid, name = functions_reply[i], functions_reply[i + 1]
                    functions[fid] = QlcFunction(fid, name)

            self.state.widgets = widgets
            self.state.functions = functions
            self.state.online = True
            self.state.last_error = None
            self.state.last_success = time.time()
        except Exception as exc:
            self.state.online = False
            self.state.last_error = f"{type(exc).__name__}: {exc}"

    # -- Control (caller must have already checked the security gate) --

    async def set_widget_value(self, widget_id: str, value: int) -> None:
        """Direct widget value set (Buttons: 0/255, Audio Triggers: 0/255,
        Sliders: 0-255). High-rate command, no "QLC+API|" prefix -- verified
        against Test_Web_API.html's vcWidgetSetValue()."""
        value = max(0, min(255, int(value)))
        async with self._lock:
            ws = await self._ensure_connected()
            await ws.send_str(f"{widget_id}|{value}")
        self.state.last_command = {"kind": "widget_value", "target": str(widget_id), "value": value, "status": "sent_unconfirmed", "at": time.time(), "evidence": "QLC+ high-rate write has no request/response acknowledgement"}

    async def cue_list_control(self, widget_id: str, operation: str, step: int | None = None) -> None:
        """operation: 'PLAY', 'NEXT', 'PREV', or 'STEP' (requires step)."""
        operation = operation.upper()
        if operation not in {"PLAY", "NEXT", "PREV", "STEP"}:
            raise ValueError("operation must be PLAY, NEXT, PREV or STEP")
        async with self._lock:
            ws = await self._ensure_connected()
            if operation == "STEP":
                if step is None:
                    raise ValueError("STEP operation requires a step index")
                await ws.send_str(f"{widget_id}|STEP|{int(step)}")
            else:
                await ws.send_str(f"{widget_id}|{operation}")
        self.state.last_command = {"kind": "cue_list", "target": str(widget_id), "operation": operation, "step": step, "status": "sent_unconfirmed", "at": time.time(), "evidence": "QLC+ high-rate write has no request/response acknowledgement"}

    async def frame_control(self, widget_id: str, operation: str) -> None:
        """operation: 'NEXT_PG' or 'PREV_PG' (multipage Frame widgets)."""
        operation = operation.upper()
        if operation not in {"NEXT_PG", "PREV_PG"}:
            raise ValueError("operation must be NEXT_PG or PREV_PG")
        async with self._lock:
            ws = await self._ensure_connected()
            await ws.send_str(f"{widget_id}|{operation}")
        self.state.last_command = {"kind": "frame", "target": str(widget_id), "operation": operation, "status": "sent_unconfirmed", "at": time.time(), "evidence": "QLC+ high-rate write has no request/response acknowledgement"}

    async def set_function_status(self, function_id: str, running: bool) -> None:
        reply = await self._query("setFunctionStatus", str(function_id), "1" if running else "0")
        if reply is None:
            self.state.last_command = {"kind": "function_status", "target": str(function_id), "running": bool(running), "status": "timeout_unconfirmed", "at": time.time(), "evidence": "No matching QLC+ API response received"}
            raise TimeoutError("QLC+ did not confirm setFunctionStatus")
        self.state.last_command = {"kind": "function_status", "target": str(function_id), "running": bool(running), "status": "confirmed_response", "at": time.time(), "evidence": "Matching QLC+ API response received"}

    async def stop(self) -> None:
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    def snapshot(self) -> dict[str, Any]:
        return {
            "qlcplus": {
                "host": self.state.host,
                "port": self.state.port,
                "online": self.state.online,
                "last_error": self.state.last_error,
                "last_success": self.state.last_success,
                "last_command": dict(self.state.last_command) if self.state.last_command else None,
                "widget_count": len(self.state.widgets),
                "function_count": len(self.state.functions),
                "widgets": [
                    {"widget_id": w.widget_id, "name": w.name, "type": w.widget_type, "status": w.status}
                    for w in self.state.widgets.values()
                ],
                "functions": [
                    {"function_id": f.function_id, "name": f.name, "type": f.function_type, "status": f.status}
                    for f in self.state.functions.values()
                ],
            }
        }
