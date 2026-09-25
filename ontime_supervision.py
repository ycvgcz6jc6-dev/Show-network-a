"""Passive Ontime run-of-show supervision.

Ontime (getontime.no) is a real, documented show-timing/rundown tool with
an HTTP poll endpoint: GET http://<host>:<port>/api/poll returns its full
"runtime data" object. This module polls that endpoint read-only and
exposes exactly the fields Ontime documents -- see
https://docs.getontime.no/api/data/runtime-data/ -- nothing more. Fields
not present in a given response are left None rather than guessed.

This is passive supervision only (matching this project's DMX-side
convention of never mixing supervision and emission): Ontime also has an
HTTP/OSC/WebSocket *control* API (starting/stopping playback, editing the
rundown) which this module deliberately does not touch. If active control
of Ontime is ever wanted, it belongs in its own explicitly-gated module,
the same way DMX output is kept separate from DMX supervision elsewhere
in this project.

Default port: Ontime's own documentation examples use 4001 for the local
server (e.g. its MCP endpoint at http://localhost:4001/mcp); the HTTP
API/poll endpoint shares that same server and port.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

DEFAULT_PORT = 4001
DEFAULT_TIMEOUT = 3.0
MAX_BODY = 2 * 1024 * 1024  # generous for a small JSON status object, not unbounded


@dataclass
class OntimeState:
    host: str
    port: int
    online: bool = False
    last_error: str | None = None
    last_poll: float | None = None
    last_success: float | None = None
    # ontime-clock
    clock_ms: int | None = None
    # ontime-timer
    timer_playback: str | None = None  # 'play' | 'pause' | 'armed' | 'stop' | 'roll'
    timer_current_ms: int | None = None
    timer_duration_ms: int | None = None
    timer_elapsed_ms: int | None = None
    timer_added_ms: int | None = None
    timer_started_at_ms: int | None = None
    timer_expected_finish_ms: int | None = None
    timer_finished_at_ms: int | None = None
    # ontime-message
    message_timer_text: str | None = None
    message_timer_visible: bool | None = None
    message_timer_blackout: bool | None = None
    message_secondary: str | None = None
    # ontime-rundown
    rundown_num_events: int | None = None
    rundown_selected_index: int | None = None
    rundown_planned_start_ms: int | None = None
    rundown_planned_end_ms: int | None = None
    rundown_actual_start_ms: int | None = None
    rundown_offset_ms: int | None = None
    rundown_expected_end_ms: int | None = None
    # ontime-offset (schedule adherence -- this is the "are we running late" figure)
    offset_absolute_ms: int | None = None
    offset_relative_ms: int | None = None
    offset_mode: str | None = None  # 'absolute' | 'relative'

    def public(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        return d


class OntimeMonitor:
    """Passive poller for one Ontime instance's /api/poll endpoint."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, *, timeout: float = DEFAULT_TIMEOUT,
                 source_ip: str | None = None) -> None:
        self.host = str(host).strip()
        self.port = int(port)
        self.timeout = max(0.5, min(10.0, float(timeout)))
        self.source_ip = source_ip or None
        self.state = OntimeState(self.host, self.port)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(local_addr=(self.source_ip, 0) if self.source_ip else None, limit=2)
            self._session = aiohttp.ClientSession(
                connector=connector, trust_env=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def async_update(self) -> None:
        self.state.last_poll = time.time()
        try:
            session = await self._get_session()
            url = f"http://{self.host}:{self.port}/api/poll"
            async with session.get(url, headers={"User-Agent": "Show-Network/ontime-readonly", "Accept": "application/json"}) as resp:
                if resp.status != 200:
                    raise OSError(f"Ontime HTTP {resp.status}")
                body = bytearray()
                async for chunk in resp.content.iter_chunked(16384):
                    body.extend(chunk)
                    if len(body) > MAX_BODY:
                        raise ValueError("Ontime /api/poll response exceeds 2 MiB")
                import json
                payload = json.loads(bytes(body).decode("utf-8", errors="replace"))
        except Exception as exc:
            self.state.online = False
            self.state.last_error = f"{type(exc).__name__}: {exc}"
            return

        # The poll endpoint documents the same shape as the WebSocket
        # runtime-data object; tolerate either the bare object or one
        # wrapped as {"payload": {...}} since Ontime's own examples show
        # WebSocket messages wrapped that way and this was not confirmed
        # firsthand against a live poll response.
        data = payload.get("payload", payload) if isinstance(payload, dict) else {}

        clock = data.get("clock")
        timer = data.get("timer") or {}
        message = data.get("message") or {}
        message_timer = message.get("timer") or {}
        rundown = data.get("rundown") or {}
        offset = data.get("offset") or {}

        self.state.online = True
        self.state.last_error = None
        self.state.last_success = time.time()
        self.state.clock_ms = clock if isinstance(clock, (int, float)) else None
        self.state.timer_playback = timer.get("playback")
        self.state.timer_current_ms = timer.get("current")
        self.state.timer_duration_ms = timer.get("duration")
        self.state.timer_elapsed_ms = timer.get("elapsed")
        self.state.timer_added_ms = timer.get("addedTime")
        self.state.timer_started_at_ms = timer.get("startedAt")
        self.state.timer_expected_finish_ms = timer.get("expectedFinish")
        self.state.timer_finished_at_ms = timer.get("finishedAt")
        self.state.message_timer_text = message_timer.get("text")
        self.state.message_timer_visible = message_timer.get("visible")
        self.state.message_timer_blackout = message_timer.get("blackout")
        self.state.message_secondary = message.get("secondary")
        self.state.rundown_num_events = rundown.get("numEvents")
        self.state.rundown_selected_index = rundown.get("selectedEventIndex")
        self.state.rundown_planned_start_ms = rundown.get("plannedStart")
        self.state.rundown_planned_end_ms = rundown.get("plannedEnd")
        self.state.rundown_actual_start_ms = rundown.get("actualStart")
        self.state.rundown_offset_ms = rundown.get("offset")
        self.state.rundown_expected_end_ms = rundown.get("expectedEnd")
        self.state.offset_absolute_ms = offset.get("absolute")
        self.state.offset_relative_ms = offset.get("relative")
        self.state.offset_mode = offset.get("mode")

    async def stop(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def snapshot(self) -> dict[str, Any]:
        return {"ontime": self.state.public()}
