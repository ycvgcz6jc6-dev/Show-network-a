"""Persistent Show Control cue bank for OSC, MIDI and Home Assistant actions."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {"ha_service", "osc", "midi", "dmx_scene"}
MAX_CUES = 128
MAX_ACTIONS_PER_CUE = 32


@dataclass
class ShowControlCue:
    cue_id: str
    name: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    enabled: bool = True


class ShowControlBank:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.enabled = False
        self.cues: dict[str, ShowControlCue] = {}
        self.fired = 0
        self.errors = 0
        self.last_cue: str | None = None
        self.last_error: str | None = None

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            rows = raw.get("cues", []) if isinstance(raw, dict) else []
            loaded: dict[str, ShowControlCue] = {}
            for item in rows[:MAX_CUES]:
                cue = ShowControlCue(**item)
                self._validate(cue)
                loaded[cue.cue_id] = cue
            self.cues = loaded
        except (OSError, ValueError, TypeError, KeyError):
            self.cues = {}
        # Safety: never re-arm active show control after restart.
        self.enabled = False

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"cues": [asdict(x) for x in self.cues.values()]}, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _validate(cue: ShowControlCue) -> None:
        if not cue.cue_id or len(cue.cue_id) > 64:
            raise ValueError("cue_id must be 1..64 characters")
        if len(cue.actions) > MAX_ACTIONS_PER_CUE:
            raise ValueError(f"A Show Control cue is limited to {MAX_ACTIONS_PER_CUE} actions")
        for action in cue.actions:
            if not isinstance(action, dict) or action.get("type") not in ALLOWED_ACTIONS:
                raise ValueError("Unsupported Show Control action")
            delay = float(action.get("delay_s", 0.0))
            if delay < 0 or delay > 300:
                raise ValueError("delay_s must be between 0 and 300 seconds")

    def upsert(self, cue: ShowControlCue) -> None:
        self._validate(cue)
        if cue.cue_id not in self.cues and len(self.cues) >= MAX_CUES:
            raise ValueError(f"Show Control is limited to {MAX_CUES} cues")
        self.cues[cue.cue_id] = cue

    def remove(self, cue_id: str) -> None:
        self.cues.pop(str(cue_id), None)

    def snapshot(self) -> dict[str, Any]:
        return {
            "show_control_enabled": self.enabled,
            "show_control_cues": [asdict(x) for x in self.cues.values()],
            "show_control_cue_count": len(self.cues),
            "show_control_fired": self.fired,
            "show_control_errors": self.errors,
            "show_control_last_cue": self.last_cue,
            "show_control_last_error": self.last_error,
        }
