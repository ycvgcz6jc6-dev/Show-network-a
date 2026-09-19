"""Passive PunchLight LAN/MIDI state monitor.

PunchLight DLi-LAN is a network MIDI (RTP-MIDI/Apple MIDI) device. The
integration intentionally does not implement RTP-MIDI transport itself; it
uses an explicitly selected MIDI input exposed by the host and observes the
PunchLight control messages. This keeps the runtime receive-only and isolated.
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from typing import Awaitable, Callable

_LOGGER = logging.getLogger(__name__)

PUNCHLIGHT_RECORD_NOTE = 95
PUNCHLIGHT_READY_NOTE = 94


class PunchLightState:
    def __init__(
        self,
        port_name: str,
        on_change: Callable[[dict], Awaitable[None] | None],
        source_name: str | None = None,
    ) -> None:
        self.port_name = port_name
        self.source_name = source_name or port_name
        self.on_change = on_change
        self._port = None
        self._task: asyncio.Task | None = None
        self.recording = False
        self.ready = False
        self.last_message = None
        self.last_error: str | None = None
        self.messages = 0
        self.last_message_at: float | None = None
        self._callback_tasks: set[asyncio.Task] = set()

    @staticmethod
    def list_input_ports() -> list[str]:
        try:
            import mido
            return list(mido.get_input_names())
        except Exception:
            return []

    def snapshot(self) -> dict:
        return {
            "configured": bool(self.port_name),
            "connected": self._port is not None,
            "port": self.port_name,
            "recording": self.recording,
            "ready": self.ready,
            "messages": self.messages,
            "last_message": self.last_message,
            "last_message_at": self.last_message_at,
            "last_message_age_s": round(max(0.0, time.time() - self.last_message_at), 3) if self.last_message_at else None,
            "healthy": self._port is not None and self.last_error is None,
            "last_error": self.last_error,
        }

    async def async_start(self) -> bool:
        if not self.port_name:
            return False
        try:
            import mido
            self._port = await asyncio.to_thread(mido.open_input, self.port_name)
            self.last_error = None
            self._task = asyncio.create_task(
                self._reader(), name=f"show-network-punchlight-{self.source_name}"
            )
            return True
        except Exception as exc:
            self.last_error = str(exc)
            await self.async_stop()
            return False

    async def _reader(self) -> None:
        while self._port is not None:
            try:
                for msg in list(self._port.iter_pending()):
                    self._handle_message(msg)
                self.last_error = None
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = str(exc)
                _LOGGER.warning("PunchLight input error on %s: %s", self.port_name, exc)
                await asyncio.sleep(0.25)

    def _handle_message(self, msg) -> None:
        typ = getattr(msg, "type", "")
        if typ not in ("note_on", "note_off"):
            return
        channel = int(getattr(msg, "channel", 0))
        note = int(getattr(msg, "note", -1))
        velocity = int(getattr(msg, "velocity", 0))
        on = typ == "note_on" and velocity > 0
        changed = False
        if channel == 0 and note == PUNCHLIGHT_RECORD_NOTE:
            changed = self.recording != on
            self.recording = on
        elif channel == 0 and note == PUNCHLIGHT_READY_NOTE:
            changed = self.ready != on
            self.ready = on
        else:
            return
        self.messages += 1
        self.last_message_at = time.time()
        self.last_message = {"type": typ, "channel": channel + 1, "note": note, "velocity": velocity}
        if changed:
            result = self.on_change(self.snapshot())
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result, name=f"show-network-punchlight-change-{self.source_name}")
                self._callback_tasks.add(task)
                task.add_done_callback(self._callback_tasks.discard)

    async def async_stop(self) -> None:
        for task in list(self._callback_tasks):
            task.cancel()
        if self._callback_tasks:
            await asyncio.gather(*self._callback_tasks, return_exceptions=True)
        self._callback_tasks.clear()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._port is not None:
            with suppress(Exception):
                self._port.close()
            self._port = None
