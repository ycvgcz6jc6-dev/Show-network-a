"""Theatrical Show Control cue bank.

A cue chains one or more actions -- a Home Assistant service call, an OSC
message, a MIDI message, or recalling a DMX scene from dmx_scene_bank.py --
behind a single numbered "GO". This is deliberately distinct from rules.py
(continuous DMX-value triggers) and dmx_ha_zones.py (continuous DMX->light
mapping): a cue only fires once per explicit GO, like a theatrical cue
stack.

Like every other action-producing module in this codebase, ShowControlBank
never executes anything itself -- it only returns the ShowControlAction list
due for the newly active cue. coordinator.py's already-gated dispatchers
(``_execute_ha_mapping`` / ``_ha_dispatcher``, the OSC/MIDI outputs, the DMX
scene bank) remain the only place anything actually gets sent.

The constructor intentionally takes only a storage path (matching
coordinator.py's ``ShowControlBank(hass.config.path(...))`` call) and has no
access to the event loop, so auto-follow ("advance N seconds after this
cue fires on its own") is stored as data on the cue for a caller with an
event loop (coordinator.py) to act on, rather than scheduled internally.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

_VALID_KINDS = ("ha_service", "osc", "midi", "dmx_scene")


@dataclass(frozen=True)
class ShowControlAction:
    kind: str  # one of _VALID_KINDS
    domain: str | None = None
    service: str | None = None
    entity_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    osc_target: str | None = None
    osc_address: str | None = None
    osc_args: tuple[Any, ...] = field(default_factory=tuple)
    midi_target: str | None = None
    midi_message: dict[str, Any] | None = None
    dmx_scene_index: int | None = None

    def __post_init__(self):
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"unsupported show control action kind: {self.kind!r}")


@dataclass
class ShowControlCue:
    cue_id: str
    number: str  # theatrical cue number, e.g. "1", "1.5", "12" -- string, operator-defined ordering
    name: str = ""
    notes: str = ""
    actions: tuple[ShowControlAction, ...] = field(default_factory=tuple)
    auto_follow_s: float | None = None
    last_fired: float | None = field(default=None, compare=False)

    def snapshot(self) -> dict:
        return {
            "cue_id": self.cue_id,
            "number": self.number,
            "name": self.name,
            "notes": self.notes,
            "actions": [asdict(a) for a in self.actions],
            "auto_follow_s": self.auto_follow_s,
            "last_fired": self.last_fired,
        }


def _action_from_dict(data: dict) -> ShowControlAction:
    data = dict(data)
    if "osc_args" in data:
        data["osc_args"] = tuple(data["osc_args"])
    return ShowControlAction(**data)


def _cue_from_dict(data: dict) -> ShowControlCue:
    data = dict(data)
    data.pop("last_fired", None)
    actions = tuple(_action_from_dict(a) for a in data.pop("actions", []) or [])
    return ShowControlCue(actions=actions, **data)


class ShowControlBank:
    """Ordered cue stack with a current-position cursor and JSON persistence."""

    def __init__(self, storage_path: str | Path) -> None:
        self.path = Path(storage_path)
        self.cues: dict[str, ShowControlCue] = {}
        self.order: list[str] = []
        self.current_index: int = -1  # -1 = standby, before the first cue
        self._history: list[dict[str, Any]] = []
        self.load()

    # -- persistence -----------------------------------------------------------
    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            _LOGGER.warning("Could not read %s, starting with an empty cue bank", self.path)
            return
        cues_raw = raw.get("cues", []) if isinstance(raw, dict) else []
        order: list[str] = []
        for item in cues_raw:
            try:
                cue = _cue_from_dict(item)
            except (TypeError, ValueError):
                _LOGGER.warning("Skipping malformed saved cue", exc_info=True)
                continue
            self.cues[cue.cue_id] = cue
            order.append(cue.cue_id)
        self.order = order
        if isinstance(raw, dict):
            self.current_index = int(raw.get("current_index", -1))
            if not -1 <= self.current_index < len(self.order):
                self.current_index = -1

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cues": [self.cues[cid].snapshot() for cid in self.order if cid in self.cues],
            "current_index": self.current_index,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # -- editing ---------------------------------------------------------------
    def add_cue(self, cue: ShowControlCue, *, position: int | None = None) -> None:
        self.cues[cue.cue_id] = cue
        if cue.cue_id in self.order:
            self.order.remove(cue.cue_id)
        if position is None:
            self.order.append(cue.cue_id)
        else:
            self.order.insert(max(0, min(position, len(self.order))), cue.cue_id)
        self.save()

    def remove_cue(self, cue_id: str) -> None:
        self.cues.pop(cue_id, None)
        if cue_id in self.order:
            idx = self.order.index(cue_id)
            self.order.remove(cue_id)
            if self.current_index >= idx:
                self.current_index = max(-1, self.current_index - 1)
        self.save()

    def reorder(self, order: list[str]) -> None:
        valid = [cid for cid in order if cid in self.cues]
        missing = [cid for cid in self.order if cid not in valid]
        self.order = valid + missing
        self.save()

    @staticmethod
    def new_cue_id() -> str:
        return uuid.uuid4().hex[:12]

    # -- playback ---------------------------------------------------------------
    def go(self, target: str | int | None = None) -> list[ShowControlAction]:
        """Advance playback and return the actions due for the newly active cue.

        ``target`` may be a cue_id, a numeric index into ``order``, or None to
        simply advance to the next cue after the current one.

        Deliberately does not call ``save()``: writing to disk on every GO
        would add blocking I/O latency to a live cue call. Cue *definitions*
        are persisted whenever they are edited (add_cue/remove_cue/reorder);
        the playback cursor is in-memory only unless a caller explicitly
        calls ``save()`` (e.g. periodically, or before a planned restart).
        """
        if not self.order:
            return []
        if target is None:
            next_index = self.current_index + 1
        elif isinstance(target, int):
            next_index = target
        else:
            try:
                next_index = self.order.index(str(target))
            except ValueError:
                _LOGGER.warning("show_control.go(): unknown cue id %r", target)
                return []
        if not 0 <= next_index < len(self.order):
            return []
        self.current_index = next_index
        cue = self.cues[self.order[next_index]]
        cue.last_fired = time.time()
        self._history.append({"ts": cue.last_fired, "cue_id": cue.cue_id, "number": cue.number, "name": cue.name})
        self._history = self._history[-100:]
        return list(cue.actions)

    def back(self) -> list[ShowControlAction]:
        if self.current_index <= 0:
            self.current_index = -1
            return []
        return self.go(self.current_index - 1)

    def reset(self) -> None:
        self.current_index = -1

    @property
    def current_cue(self) -> ShowControlCue | None:
        if 0 <= self.current_index < len(self.order):
            return self.cues.get(self.order[self.current_index])
        return None

    # -- reporting -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        current = self.current_cue
        return {
            "show_control_cues": [self.cues[cid].snapshot() for cid in self.order if cid in self.cues],
            "show_control_cue_count": len(self.order),
            "show_control_current_cue": current.cue_id if current else None,
            "show_control_current_number": current.number if current else None,
            "show_control_history": list(self._history[-20:]),
        }
