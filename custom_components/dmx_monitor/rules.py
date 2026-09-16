"""DMX-value-triggered rule engine.

A Rule watches one DMX universe/source for a set of channel conditions
(all AND-ed together). It fires ``action`` on the rising edge (conditions
become true after having been false) and, optionally, ``action_off`` on the
falling edge. This is deliberately separate from dmx_ha_mapping.py /
dmx_ha_zones.py (continuous value -> light state mapping): a Rule is a
discrete trigger, evaluated only when its conditions transition, with a
cooldown to avoid re-firing on every single DMX frame.

Like the rest of this codebase, the rule engine only ever proposes a
RuleAction; it never calls a Home Assistant service itself. coordinator.py's
``_execute_rule_action`` is the single, security-gated place that actually
dispatches to Home Assistant.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

_VALID_OPS = (">=", "<=", "==", "!=", ">", "<")


def _compare(value: int, op: str, threshold: int) -> bool:
    if op == ">=":
        return value >= threshold
    if op == "<=":
        return value <= threshold
    if op == "==":
        return value == threshold
    if op == "!=":
        return value != threshold
    if op == ">":
        return value > threshold
    if op == "<":
        return value < threshold
    raise ValueError(f"Unsupported rule operator: {op!r}")


@dataclass(frozen=True)
class RuleCondition:
    channel: int  # 1-512, DMX channel number (not zero-based index)
    op: str
    value: int

    def __post_init__(self):
        if not 1 <= self.channel <= 512:
            raise ValueError("channel must be 1..512")
        if self.op not in _VALID_OPS:
            raise ValueError(f"unsupported operator: {self.op!r}")
        if not 0 <= self.value <= 255:
            raise ValueError("value must be 0..255")

    def evaluate(self, frame: bytes) -> bool:
        actual = frame[self.channel - 1] if self.channel - 1 < len(frame) else 0
        return _compare(actual, self.op, self.value)


@dataclass(frozen=True)
class RuleAction:
    domain: str
    service: str
    entity_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    name: str
    protocol: str = "*"  # "*" matches any protocol
    universe: int = 1
    source: str | None = None  # None matches any source
    conditions: tuple[RuleCondition, ...] = field(default_factory=tuple)
    action: RuleAction | None = None
    action_off: RuleAction | None = None
    cooldown_s: float = 2.0
    enabled: bool = True

    # -- runtime state, not persisted as rule configuration -----------------
    matched: bool = field(default=False, compare=False)
    last_triggered: float | None = field(default=None, compare=False)
    last_evaluated: float | None = field(default=None, compare=False)

    def matches_source(self, protocol: str, universe: int, source: str | None) -> bool:
        if not self.enabled:
            return False
        if self.protocol != "*" and self.protocol.lower() != str(protocol).lower():
            return False
        if self.universe != universe:
            return False
        if self.source is not None and self.source != source:
            return False
        return True

    def evaluate_conditions(self, frame: bytes) -> bool:
        if not self.conditions:
            return False
        return all(c.evaluate(frame) for c in self.conditions)

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "protocol": self.protocol,
            "universe": self.universe,
            "source": self.source,
            "conditions": [asdict(c) for c in self.conditions],
            "action": asdict(self.action) if self.action else None,
            "action_off": asdict(self.action_off) if self.action_off else None,
            "cooldown_s": self.cooldown_s,
            "enabled": self.enabled,
            "matched": self.matched,
            "last_triggered": self.last_triggered,
        }


@dataclass
class RuleEvalResult:
    rule_name: str
    matched: bool
    transitioned: bool
    action_due: RuleAction | None = None


class RuleSet:
    """Holds rules and evaluates them against each observed DMX frame."""

    def __init__(self, *, trace_limit: int = 200) -> None:
        self.rules: dict[str, Rule] = {}
        self._trace: list[dict] = []
        self._trace_limit = int(trace_limit)

    # -- configuration -------------------------------------------------------
    def add(self, rule: Rule) -> None:
        self.rules[rule.name] = rule

    def remove(self, name: str) -> None:
        self.rules.pop(name, None)

    def set_rules(self, rules: list[Rule]) -> None:
        self.rules = {r.name: r for r in rules}

    # -- evaluation ------------------------------------------------------------
    def evaluate_snapshot(self, protocol: str, universe: int, source: str | None, values: bytes) -> list[RuleEvalResult]:
        now = time.time()
        frame = bytes(values[:512])
        results: list[RuleEvalResult] = []
        for rule in self.rules.values():
            if not rule.matches_source(protocol, universe, source):
                continue
            rule.last_evaluated = now
            currently_matched = rule.evaluate_conditions(frame)
            was_matched = rule.matched
            action_due = None
            transitioned = currently_matched != was_matched
            if transitioned:
                cooled_down = rule.last_triggered is None or (now - rule.last_triggered) >= rule.cooldown_s
                if currently_matched and rule.action and cooled_down:
                    action_due = rule.action
                    rule.last_triggered = now
                elif not currently_matched and rule.action_off and cooled_down:
                    action_due = rule.action_off
                    rule.last_triggered = now
            rule.matched = currently_matched
            result = RuleEvalResult(rule_name=rule.name, matched=currently_matched, transitioned=transitioned, action_due=action_due)
            results.append(result)
            if transitioned:
                self._trace.append({
                    "ts": now, "rule": rule.name, "matched": currently_matched,
                    "action_fired": action_due is not None,
                })
                self._trace = self._trace[-self._trace_limit:]
        return results

    # -- reporting -------------------------------------------------------------
    def snapshot(self) -> list[dict]:
        return [rule.snapshot() for rule in self.rules.values()]

    def trace_snapshot(self) -> list[dict]:
        return list(self._trace[-50:])
