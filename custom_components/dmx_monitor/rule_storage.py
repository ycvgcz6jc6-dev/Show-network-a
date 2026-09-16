"""Persistence for DMX rule engine configuration (rules.py)."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from .rules import Rule, RuleAction, RuleCondition

_LOGGER = logging.getLogger(__name__)


class RuleStore:
    def __init__(self, hass_config_path: str) -> None:
        self.path = Path(hass_config_path) / "show_network_rules.json"
        self._last_payload: str | None = None

    def load(self) -> list[Rule]:
        if not self.path.exists():
            return []
        try:
            raw_text = self.path.read_text(encoding="utf-8")
            self._last_payload = raw_text
            raw = json.loads(raw_text)
        except (OSError, ValueError, TypeError):
            _LOGGER.warning("Could not read %s, starting with no saved rules", self.path)
            return []
        out: list[Rule] = []
        for item in raw if isinstance(raw, list) else []:
            try:
                data = dict(item)
                conditions = tuple(RuleCondition(**c) for c in data.pop("conditions", []) or [])
                action_data = data.pop("action", None)
                action_off_data = data.pop("action_off", None)
                # Drop runtime-only fields a previous snapshot() may have
                # included; Rule() does not accept them as constructor args.
                data.pop("matched", None)
                data.pop("last_triggered", None)
                rule = Rule(
                    conditions=conditions,
                    action=RuleAction(**action_data) if action_data else None,
                    action_off=RuleAction(**action_off_data) if action_off_data else None,
                    **data,
                )
                out.append(rule)
            except (TypeError, ValueError):
                _LOGGER.warning("Skipping malformed saved rule entry", exc_info=True)
        return out

    def save(self, rules: list[Rule]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps([r.snapshot() for r in rules], ensure_ascii=False, indent=2)
        if raw == self._last_payload and self.path.exists():
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(raw, encoding="utf-8")
        tmp.replace(self.path)
        self._last_payload = raw

    async def async_save(self, rules: list[Rule]) -> None:
        await asyncio.to_thread(self.save, rules)

    async def async_load(self) -> list[Rule]:
        return await asyncio.to_thread(self.load)
