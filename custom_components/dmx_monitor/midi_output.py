"""Explicitly armed MIDI OUT for Show Network.

MIDI output is disabled after every restart. Ports are opened only for the
individual send operation so Show Network does not monopolize a device.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass
class MIDITarget:
    target_id: str
    name: str
    port_name: str
    enabled: bool = True


class MIDITargetStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> list[MIDITarget]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [MIDITarget(**item) for item in raw if isinstance(item, dict)]
        except (OSError, ValueError, TypeError):
            return []

    def save(self, targets: list[MIDITarget]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(t) for t in targets], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


class MIDIOutput:
    def __init__(self) -> None:
        self.enabled = False
        self.sent = 0
        self.errors = 0
        self.last_target: str | None = None
        self.last_message: dict[str, Any] | None = None
        self.last_error: str | None = None

    @staticmethod
    def list_output_ports() -> list[str]:
        try:
            import mido
            return list(mido.get_output_names())
        except Exception:
            return []

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    @staticmethod
    def _build_message(message_type: str, data: dict[str, Any]):
        import mido
        typ = str(message_type)
        channel = int(data.get("channel", 1)) - 1
        if not 0 <= channel <= 15:
            raise ValueError("MIDI channel must be 1..16")
        if typ == "control_change":
            return mido.Message(typ, channel=channel, control=int(data["control"]), value=int(data["value"]))
        if typ in ("note_on", "note_off"):
            return mido.Message(typ, channel=channel, note=int(data["note"]), velocity=int(data.get("velocity", 127 if typ == "note_on" else 0)))
        if typ == "program_change":
            return mido.Message(typ, channel=channel, program=int(data["program"]))
        if typ == "pitchwheel":
            return mido.Message(typ, channel=channel, pitch=int(data["pitch"]))
        raise ValueError(f"Unsupported MIDI OUT message type: {typ}")

    async def async_send(self, target: MIDITarget, message_type: str, data: dict[str, Any]) -> None:
        if not self.enabled:
            raise RuntimeError("MIDI output safety gate is disabled")
        if not target.enabled:
            raise RuntimeError("MIDI target is disabled")

        def _send() -> None:
            import mido
            message = self._build_message(message_type, data)
            port = mido.open_output(target.port_name)
            try:
                port.send(message)
            finally:
                port.close()

        try:
            await asyncio.to_thread(_send)
            self.sent += 1
            self.last_target = target.target_id
            self.last_message = {"type": str(message_type), **dict(data)}
            self.last_error = None
        except Exception as exc:
            self.errors += 1
            self.last_error = str(exc)
            raise

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "sent": self.sent,
            "errors": self.errors,
            "last_target": self.last_target,
            "last_message": self.last_message,
            "last_error": self.last_error,
        }
