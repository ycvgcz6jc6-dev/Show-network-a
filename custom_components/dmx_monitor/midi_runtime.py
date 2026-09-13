"""Optional receive-only MIDI runtime using Mido/RtMidi.

This adapter is deliberately small: it opens only an explicitly selected MIDI
input port and converts incoming messages to the integration's normalized MIDI
model. No output port is opened or written.
"""
from __future__ import annotations
import asyncio
from contextlib import suppress
from typing import Awaitable, Callable

from .midi import MIDIMessage, normalize_control_change, normalize_note, normalize_pitchwheel


class MIDIInputRuntime:
    def __init__(self, port_name: str, callback: Callable[[MIDIMessage], Awaitable[None] | None], source_name: str | None = None):
        self.port_name = port_name
        self.callback = callback
        self.source_name = source_name or port_name
        self._port = None
        self._task: asyncio.Task | None = None
        self.error: str | None = None

    @staticmethod
    def list_input_ports() -> list[str]:
        try:
            import mido
            return list(mido.get_input_names())
        except Exception:
            return []

    async def async_start(self) -> bool:
        try:
            import mido
            # RtMidi/OS device opening can block; keep it off HA's event loop.
            self._port = await asyncio.to_thread(mido.open_input, self.port_name)
            self._task = asyncio.create_task(self._reader(), name=f"show-network-midi-{self.source_name}")
            self.error = None
            return True
        except Exception as exc:
            self.error = str(exc)
            await self.async_stop()
            return False

    async def _reader(self):
        while self._port is not None:
            try:
                messages = list(self._port.iter_pending())
                for msg in messages:
                    normalized = self._normalize(msg)
                    if normalized is not None:
                        result = self.callback(normalized)
                        if asyncio.iscoroutine(result):
                            await result
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.error = str(exc)
                await asyncio.sleep(0.25)

    def _normalize(self, msg):
        typ = getattr(msg, "type", "")
        channel = getattr(msg, "channel", None)
        if typ == "control_change":
            return normalize_control_change(channel, msg.control, msg.value, self.source_name)
        if typ == "note_on":
            return normalize_note(channel, msg.note, msg.velocity, self.source_name, on=msg.velocity != 0)
        if typ == "note_off":
            return normalize_note(channel, msg.note, msg.velocity, self.source_name, on=False)
        if typ == "pitchwheel":
            return normalize_pitchwheel(channel, msg.pitch, self.source_name)
        return MIDIMessage(typ, channel, tuple(), self.source_name, 0.0)

    async def async_stop(self):
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._port is not None:
            with suppress(Exception):
                self._port.close()
            self._port = None
