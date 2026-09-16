"""Persistent storage for Show Network Rule Builder rules.

Only rule configuration is stored; runtime state/history is intentionally not
persisted so a Home Assistant restart cannot replay a stale transition.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any
from .rules import DmxAction, DmxCondition, DmxRule

FILENAME = "show_network_rules.json"


def _action(data: dict[str, Any] | None) -> DmxAction | None:
    if not data:
        return None
    return DmxAction(
        domain=str(data.get("domain", "")),
        entity_id=(str(data["entity_id"]) if data.get("entity_id") else None),
        service=str(data.get("service", "")),
        data=dict(data.get("data") or {}),
    )


def rule_from_dict(data: dict[str, Any]) -> DmxRule:
    condition = DmxCondition(
        channels=tuple(int(x) for x in data.get("channels", [])),
        mode=str(data.get("mode", "any")),
        threshold_on=int(data.get("threshold_on", 10)),
        threshold_off=data.get("threshold_off"),
        x=int(data.get("x", 1)),
    )
    return DmxRule(
        name=str(data["name"]), universe=int(data["universe"]), source=data.get("source"),
        condition=condition, action=_action(data.get("action")), off_action=_action(data.get("off_action")),
        on_delay_ms=int(data.get("on_delay_ms", 0)), off_delay_ms=int(data.get("off_delay_ms", 0)),
        enabled=bool(data.get("enabled", False)), test_mode=bool(data.get("test_mode", False)),
    )


def rule_to_dict(rule: DmxRule) -> dict[str, Any]:
    def action(a: DmxAction | None):
        return None if a is None else {"domain": a.domain, "entity_id": a.entity_id, "service": a.service, "data": a.data}
    return {
        "name": rule.name, "universe": rule.universe, "source": rule.source,
        "channels": list(rule.condition.channels), "mode": rule.condition.mode, "x": rule.condition.x,
        "threshold_on": rule.condition.threshold_on, "threshold_off": rule.condition.threshold_off,
        "on_delay_ms": rule.on_delay_ms, "off_delay_ms": rule.off_delay_ms,
        "enabled": rule.enabled, "test_mode": rule.test_mode,
        "action": action(rule.action), "off_action": action(rule.off_action),
    }


class RuleStore:
    def __init__(self, config_dir: str) -> None:
        self.path = Path(config_dir) / FILENAME
        self._last_payload: str | None = None

    def load(self) -> list[DmxRule]:
        if not self.path.exists():
            return []
        try:
            raw = self.path.read_text(encoding="utf-8")
            self._last_payload = raw
            payload = json.loads(raw)
            return [rule_from_dict(item) for item in payload.get("rules", [])]
        except (OSError, ValueError, TypeError, KeyError) as err:
            # Bad persisted configuration must not prevent HA from starting.
            return []


    async def async_load(self) -> list[DmxRule]:
        """Load rules without blocking Home Assistant's event loop."""
        return await asyncio.to_thread(self.load)

    async def async_save(self, rules: list[DmxRule]) -> None:
        """Persist rules without blocking Home Assistant's event loop."""
        await asyncio.to_thread(self.save, rules)

    def save(self, rules: list[DmxRule]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "rules": [rule_to_dict(rule) for rule in rules]}
        raw = json.dumps(payload, ensure_ascii=False, indent=2)
        if raw == self._last_payload and self.path.exists():
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(raw, encoding="utf-8")
        tmp.replace(self.path)
        self._last_payload = raw
