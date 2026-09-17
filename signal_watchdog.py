"""Signal watchdogs for receive-only show-network sources.

A watchdog watches the *presence* of valid incoming telemetry. It never
transmits DMX, sACN or Art-Net. When a source stays silent for the configured
period, an optional Home Assistant action can be executed (for example a Hue
scene). Recovery can optionally execute another action after stable signal
return.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass
class SignalWatchdogRule:
    name: str
    protocol: str
    universe: int
    source: str | None = None
    loss_timeout_s: float = 10.0
    recovery_delay_s: float = 3.0
    loss_action: dict[str, Any] | None = None
    recovery_action: dict[str, Any] | None = None
    enabled: bool = True


@dataclass(frozen=True)
class WatchdogState:
    key: str
    signal_ok: bool
    active: bool
    last_signal_age_s: float | None
    loss_timeout_s: float
    last_transition: str | None
    reason: str


class SignalWatchdogManager:
    """Manage signal-loss timers and optional HA actions."""

    def __init__(self, hass, action_guard=None, event_callback=None) -> None:
        self.hass = hass
        self.action_guard = action_guard
        self.event_callback = event_callback
        self.rules: dict[str, SignalWatchdogRule] = {}
        self._last_signal: dict[str, float] = {}
        self._states: dict[str, bool] = {}
        # Timer handles avoid creating/cancelling an asyncio Task for every
        # high-rate packet. A coroutine task is created only when a timer fires.
        self._loss_tasks: dict[str, asyncio.TimerHandle] = {}
        self._recovery_tasks: dict[str, asyncio.TimerHandle] = {}
        self._last_transition: dict[str, str | None] = {}
        self._last_reason: dict[str, str] = {}
        self._recovery_started: dict[str, float] = {}

    def add_rule(self, rule: SignalWatchdogRule) -> None:
        if rule.universe < 1:
            raise ValueError("universe must be >= 1")
        if rule.loss_timeout_s <= 0:
            raise ValueError("loss_timeout_s must be > 0")
        if rule.recovery_delay_s < 0:
            raise ValueError("recovery_delay_s must be >= 0")
        key = self._key(rule)
        self.rules[key] = rule
        self._states.setdefault(key, False)
        self._last_transition.setdefault(key, None)
        self._last_reason.setdefault(key, "waiting for first valid signal")
        # A watchdog must also detect silence from startup, before the first packet.
        try:
            loop = asyncio.get_running_loop()
            self._loss_tasks[key] = loop.call_later(rule.loss_timeout_s, self._timer_fire_loss, key)
        except RuntimeError:
            # Unit tests/non-async construction may add rules before a loop exists;
            # the first observation will arm the normal loss timer.
            pass

    def remove_rule(self, name: str) -> None:
        for key, rule in list(self.rules.items()):
            if rule.name == name:
                self._cancel(self._loss_tasks.pop(key, None))
                self._cancel(self._recovery_tasks.pop(key, None))
                self.rules.pop(key, None)
                self._last_signal.pop(key, None)
                self._states.pop(key, None)
                self._recovery_started.pop(key, None)

    def observe(self, protocol: str, universe: int, source: str | None = None) -> None:
        now = monotonic()
        for key, rule in self.rules.items():
            if rule.protocol.lower() != protocol.lower() or rule.universe != universe:
                continue
            if rule.source and rule.source != source:
                continue
            self._last_signal[key] = now
            # Recovery is only relevant while an alarm is active. Crucially,
            # continued packets do not restart the recovery delay.
            if self._states.get(key, False) and key not in self._recovery_tasks:
                if rule.recovery_delay_s:
                    self._recovery_started[key] = now
                    loop = asyncio.get_running_loop()
                    self._recovery_tasks[key] = loop.call_later(
                        rule.recovery_delay_s, self._timer_fire_recovery, key
                    )
                else:
                    self._set_recovered(key)
                    asyncio.create_task(self._run_recovery_action(key), name=f"dmx-watchdog-recovery-action-{key}")
            handle = self._loss_tasks.pop(key, None)
            self._cancel(handle)
            loop = asyncio.get_running_loop()
            self._loss_tasks[key] = loop.call_later(
                rule.loss_timeout_s, self._timer_fire_loss, key
            )

    async def simulate_loss(self, key: str | None = None) -> None:
        """Inject a logical loss for testing without touching the network."""
        selected = self._select(key)
        for k, rule in selected:
            self._cancel(self._loss_tasks.pop(k, None))
            self._cancel(self._recovery_tasks.pop(k, None))
            self._states[k] = True
            self._last_transition[k] = "simulation_loss"
            self._last_reason[k] = "SIMULATION: signal loss injected"
            await self._run_action(rule.loss_action)
            self._emit_event("simulation_loss", rule, self._last_reason[k])

    async def simulate_restore(self, key: str | None = None) -> None:
        """Inject a logical recovery for testing without touching the network."""
        selected = self._select(key)
        for k, rule in selected:
            self._cancel(self._loss_tasks.pop(k, None))
            self._cancel(self._recovery_tasks.pop(k, None))
            self._states[k] = False
            self._recovery_started.pop(k, None)
            self._last_transition[k] = "simulation_restore"
            self._last_reason[k] = "SIMULATION: signal restored"
            await self._run_action(rule.recovery_action)
            self._emit_event("simulation_restore", rule, self._last_reason[k])

    def _select(self, key: str | None):
        if key:
            if key not in self.rules:
                raise ValueError(f"Unknown watchdog: {key}")
            return [(key, self.rules[key])]
        return list(self.rules.items())

    async def async_stop(self) -> None:
        handles = list(self._loss_tasks.values()) + list(self._recovery_tasks.values())
        for handle in handles:
            self._cancel(handle)
        self._loss_tasks.clear()
        self._recovery_tasks.clear()

    def snapshot(self) -> dict[str, Any]:
        now = monotonic()
        states = []
        for key, rule in self.rules.items():
            last = self._last_signal.get(key)
            states.append({
                "key": key,
                "name": rule.name,
                "protocol": rule.protocol,
                "universe": rule.universe,
                "source": rule.source,
                "signal_ok": last is not None and now - last < rule.loss_timeout_s,
                "active": self._states.get(key, False),
                "last_signal_age_s": None if last is None else round(max(0.0, now - last), 3),
                "loss_timeout_s": rule.loss_timeout_s,
                "recovery_delay_s": rule.recovery_delay_s,
                "last_transition": self._last_transition.get(key),
                "reason": self._last_reason.get(key, ""),
                "enabled": rule.enabled,
            })
        return {"watchdog_rules": states, "watchdog_active": sum(1 for x in states if x["active"])}

    def _timer_fire_loss(self, key: str) -> None:
        self._loss_tasks.pop(key, None)
        if key in self.rules:
            asyncio.create_task(self._lose_after(key, 0), name=f"dmx-watchdog-loss-{key}")

    def _timer_fire_recovery(self, key: str) -> None:
        self._recovery_tasks.pop(key, None)
        if key in self.rules:
            asyncio.create_task(self._recover_after(key, 0), name=f"dmx-watchdog-recovery-{key}")

    async def _lose_after(self, key: str, timeout: float) -> None:
        try:
            if timeout:
                await asyncio.sleep(timeout)
            rule = self.rules.get(key)
            if not rule or not rule.enabled:
                return
            last = self._last_signal.get(key)
            if last is None or monotonic() - last >= rule.loss_timeout_s:
                if self._states.get(key, False):
                    return
                self._cancel(self._recovery_tasks.pop(key, None))
                self._recovery_started.pop(key, None)
                self._states[key] = True
                self._last_transition[key] = "signal_lost"
                self._last_reason[key] = f"No valid {rule.protocol} signal for {rule.loss_timeout_s:g}s"
                await self._run_action(rule.loss_action)
                self._emit_event("signal_lost", rule, self._last_reason[key])
        except asyncio.CancelledError:
            raise

    async def _recover_after(self, key: str, delay: float) -> None:
        try:
            if delay:
                await asyncio.sleep(delay)
            rule = self.rules.get(key)
            if not rule or not rule.enabled:
                return
            last = self._last_signal.get(key)
            started = self._recovery_started.get(key)
            # The loss timer is continuously renewed by valid packets. If it is
            # still armed here and a packet has been seen since recovery began,
            # signal has been stable for the requested recovery window.
            if self._states.get(key, False) and last is not None and started is not None and last >= started:
                self._set_recovered(key)
                self._recovery_started.pop(key, None)
                await self._run_action(rule.recovery_action)
                self._emit_event("signal_restored", rule, self._last_reason[key])
        except asyncio.CancelledError:
            raise


    async def _run_recovery_action(self, key: str) -> None:
        rule = self.rules.get(key)
        if not rule or not rule.enabled:
            return
        await self._run_action(rule.recovery_action)
        self._emit_event("signal_restored", rule, self._last_reason.get(key, "Valid signal restored"))

    def _emit_event(self, event: str, rule: SignalWatchdogRule, reason: str) -> None:
        if self.event_callback:
            try:
                self.event_callback(event, rule, reason)
            except Exception:
                pass

    def _set_recovered(self, key: str) -> None:
        self._states[key] = False
        self._last_transition[key] = "signal_restored"
        self._last_reason[key] = "Valid signal restored"

    async def _run_action(self, action: dict[str, Any] | None) -> None:
        if not action:
            return
        domain = action.get("domain")
        service = action.get("service")
        if not domain or not service:
            return
        if self.action_guard and not self.action_guard(action):
            return
        service_data = dict(action.get("data") or {})
        target = action.get("entity_id")
        if target:
            service_data.setdefault("entity_id", target)
        await self.hass.services.async_call(domain, service, service_data, blocking=False)

    @staticmethod
    def _key(rule: SignalWatchdogRule) -> str:
        return f"{rule.protocol.lower()}:{rule.universe}:{rule.source or '*'}:{rule.name}"

    @staticmethod
    def _cancel(handle: asyncio.TimerHandle | asyncio.Task | None) -> None:
        if handle and not handle.cancelled():
            handle.cancel()
