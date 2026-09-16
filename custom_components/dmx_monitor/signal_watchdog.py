"""Signal-presence watchdogs (distinct from the value-based rule engine).

A watchdog does not look at DMX *values* (rules.py does that); it only cares
whether packets for a given protocol/universe/(optional source) keep
arriving. If nothing is observed for ``timeout_s``, the watchdog declares
"signal_lost" and, if configured, calls one Home Assistant service
(``action_lost``); when packets resume it declares "signal_restored" and
optionally calls ``action_restored``. This mirrors the DMX Circuit Monitor's
OFF/ON/SIGNAL_LOST idea but at the *rule/action* level instead of the raw
per-channel level, and -- unlike the rule engine -- is allowed to call the
Home Assistant service itself directly, gated by ``action_guard``, since the
constructor is handed ``hass`` for exactly that purpose.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

_CHECK_INTERVAL_S = 1.0


@dataclass
class WatchdogRule:
    name: str
    protocol: str = "*"
    universe: int = 1
    source: str | None = None
    timeout_s: float = 5.0
    action_lost: dict[str, Any] | None = None
    action_restored: dict[str, Any] | None = None
    enabled: bool = True

    # -- runtime state -------------------------------------------------------
    last_seen: float | None = field(default=None, compare=False)
    lost: bool = field(default=False, compare=False)
    simulated_lost: bool = field(default=False, compare=False)

    def matches(self, protocol: str, universe: int, source: str | None) -> bool:
        if self.protocol != "*" and self.protocol.lower() != str(protocol).lower():
            return False
        if self.universe != universe:
            return False
        if self.source is not None and self.source != source:
            return False
        return True

    def snapshot(self, now: float) -> dict:
        age = None if self.last_seen is None else max(0.0, now - self.last_seen)
        return {
            "name": self.name,
            "protocol": self.protocol,
            "universe": self.universe,
            "source": self.source,
            "timeout_s": self.timeout_s,
            "enabled": self.enabled,
            "lost": self.lost,
            "simulated_lost": self.simulated_lost,
            "age_s": None if age is None else round(age, 1),
            "has_action_lost": self.action_lost is not None,
            "has_action_restored": self.action_restored is not None,
        }


class SignalWatchdogManager:
    """Tracks signal presence per rule and reacts on loss/restore edges."""

    def __init__(
        self,
        hass,
        *,
        action_guard: Callable[[dict[str, Any]], bool] | None = None,
        event_callback: Callable[[str, WatchdogRule, str], None] | None = None,
        check_interval_s: float = _CHECK_INTERVAL_S,
    ) -> None:
        self.hass = hass
        self.action_guard = action_guard or (lambda action: True)
        self.event_callback = event_callback
        self.check_interval_s = float(check_interval_s)
        self.rules: dict[str, WatchdogRule] = {}
        self._task: asyncio.Task | None = None

    # -- configuration -------------------------------------------------------
    def add(self, rule: WatchdogRule) -> None:
        self.rules[rule.name] = rule

    def remove(self, name: str) -> None:
        self.rules.pop(name, None)

    def set_rules(self, rules: list[WatchdogRule]) -> None:
        self.rules = {r.name: r for r in rules}

    # -- observation -----------------------------------------------------------
    def observe(self, protocol: str, universe: int, source: str | None) -> None:
        now = time.time()
        for rule in self.rules.values():
            if not rule.enabled or not rule.matches(protocol, universe, source):
                continue
            was_lost = rule.lost or rule.simulated_lost
            rule.last_seen = now
            rule.simulated_lost = False
            if was_lost:
                rule.lost = False
                self._handle_transition(rule, "signal_restored", "signal observed again")

    # -- background loop -------------------------------------------------------
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_event_loop().create_task(self._run(), name="show-network-signal-watchdog")

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.check_interval_s)
                self._check_all()
        except asyncio.CancelledError:
            return

    def _check_all(self) -> None:
        now = time.time()
        for rule in self.rules.values():
            if not rule.enabled or rule.simulated_lost:
                continue
            if rule.last_seen is None:
                continue
            if not rule.lost and (now - rule.last_seen) > rule.timeout_s:
                rule.lost = True
                self._handle_transition(rule, "signal_lost", f"no packet for {rule.timeout_s:g}s")

    def _handle_transition(self, rule: WatchdogRule, event: str, reason: str) -> None:
        if self.event_callback:
            try:
                self.event_callback(event, rule, reason)
            except Exception:
                _LOGGER.warning("Watchdog event callback failed for %s", rule.name, exc_info=True)
        action = rule.action_lost if event == "signal_lost" else rule.action_restored
        if action:
            self._dispatch_action(action)

    def _dispatch_action(self, action: dict[str, Any]) -> None:
        if not self.action_guard(action):
            return
        domain = action.get("domain")
        service = action.get("service")
        if not domain or not service:
            return
        data = dict(action.get("data") or {})
        entity_id = action.get("entity_id")
        if entity_id:
            data["entity_id"] = entity_id
        if self.hass and self.hass.services.has_service(domain, service):
            self.hass.async_create_task(self.hass.services.async_call(domain, service, data))
        else:
            _LOGGER.warning("Watchdog action service not found: %s.%s", domain, service)

    # -- simulation (for the Chaos/reliability testing tools) -------------------
    async def simulate_loss(self, key: str | None = None) -> None:
        for rule in self._targets(key):
            if not rule.lost:
                rule.lost = True
                rule.simulated_lost = True
                self._handle_transition(rule, "simulation_loss", "manually simulated signal loss")

    async def simulate_restore(self, key: str | None = None) -> None:
        for rule in self._targets(key):
            if rule.lost:
                rule.lost = False
                rule.simulated_lost = False
                rule.last_seen = time.time()
                self._handle_transition(rule, "signal_restored", "manually simulated signal restore")

    def _targets(self, key: str | None) -> list[WatchdogRule]:
        if key is None:
            return list(self.rules.values())
        rule = self.rules.get(key)
        return [rule] if rule else []

    # -- reporting -------------------------------------------------------------
    def snapshot(self) -> dict:
        now = time.time()
        rows = [r.snapshot(now) for r in self.rules.values()]
        return {
            "watchdog_rules": rows,
            "watchdog_active": sum(1 for r in rows if r["lost"]),
        }

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
