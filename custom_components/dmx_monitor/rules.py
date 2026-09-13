"""Receive-only rule engine for the Show Network integration."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

@dataclass(frozen=True)
class DmxCondition:
    channels: tuple[int, ...]
    mode: str = "any"
    threshold_on: int = 10
    threshold_off: int | None = None
    x: int = 1
    def __post_init__(self):
        if self.mode not in {"any", "all", "x_of_y"}: raise ValueError("mode must be any, all or x_of_y")
        if not self.channels or any(c < 1 or c > 512 for c in self.channels): raise ValueError("DMX channels must be 1..512")
        if not 0 <= self.threshold_on <= 255: raise ValueError("threshold_on must be 0..255")
        off = self.threshold_off if self.threshold_off is not None else self.threshold_on
        if not 0 <= off <= 255: raise ValueError("threshold_off must be 0..255")
        if self.mode == "x_of_y" and not 1 <= self.x <= len(self.channels): raise ValueError("x must be within selected channels")

@dataclass(frozen=True)
class DmxAction:
    domain: str
    service: str
    entity_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class DmxRule:
    name: str
    universe: int
    condition: DmxCondition
    action: DmxAction | None = None
    off_action: DmxAction | None = None
    source: str | None = None
    on_delay_ms: int = 0
    off_delay_ms: int = 0
    enabled: bool = False
    test_mode: bool = False

@dataclass(frozen=True)
class RuleTrace:
    active: bool; target: bool; selected: tuple[int, ...]; active_channels: tuple[int, ...]
    count_active: int; required: int; threshold: int; pending: str | None; reason: str

class DmxRuleEvaluator:
    def __init__(self, rule: DmxRule):
        self.rule = rule; self.state = False; self._candidate_since: float | None = None
    def _required(self) -> int:
        n = len(self.rule.condition.channels)
        return n if self.rule.condition.mode == "all" else (self.rule.condition.x if self.rule.condition.mode == "x_of_y" else 1)
    def evaluate(self, values: list[int] | bytes, now: float | None = None) -> RuleTrace:
        c=self.rule.condition; now=monotonic() if now is None else now
        threshold=c.threshold_off if (self.state and c.threshold_off is not None) else c.threshold_on
        comparison = (lambda value: value >= threshold) if not self.state else (lambda value: value > threshold)
        active_channels=tuple(ch for ch in c.channels if ch <= len(values) and comparison(int(values[ch-1])))
        count=len(active_channels); required=self._required(); target=count >= required; pending=None
        if target != self.state:
            if self._candidate_since is None: self._candidate_since=now
            delay_ms=self.rule.on_delay_ms if target else self.rule.off_delay_ms
            if (now-self._candidate_since)*1000 >= max(0, delay_ms): self.state=target; self._candidate_since=None
            else: pending="on" if target else "off"
        else: self._candidate_since=None
        reason=(f"{count}/{len(c.channels)} selected channels meet threshold {threshold}" if not pending else f"target {'ON' if target else 'OFF'} pending ({pending} delay)")
        return RuleTrace(self.state,target,c.channels,active_channels,count,required,threshold,pending,reason)

def parse_channel_selection(text: str) -> tuple[int, ...]:
    result=set()
    for part in text.replace(" ","").split(","):
        if not part: continue
        if "-" in part:
            a,b=part.split("-",1); start,end=int(a),int(b); result.update(range(min(start,end),max(start,end)+1))
        else: result.add(int(part))
    if not result or any(c<1 or c>512 for c in result): raise ValueError("selection must contain DMX channels 1..512")
    return tuple(sorted(result))


@dataclass
class RuleEvaluation:
    """Result of evaluating a named rule against one DMX snapshot."""
    rule_name: str
    trace: RuleTrace
    action_due: DmxAction | None = None
    transitioned: bool = False


class RuleSet:
    """In-memory collection of DMX rules with safe simulation and tracing."""
    def __init__(self) -> None:
        self.rules: dict[str, DmxRule] = {}
        self._evaluators: dict[str, DmxRuleEvaluator] = {}
        self.history: list[RuleEvaluation] = []
        self.max_history = 200

    def add(self, rule: DmxRule) -> None:
        if not rule.name.strip():
            raise ValueError("rule name cannot be empty")
        self.rules[rule.name] = rule
        self._evaluators[rule.name] = DmxRuleEvaluator(rule)

    def update(self, name: str, rule: DmxRule) -> None:
        """Replace a rule definition while resetting its runtime evaluator safely."""
        if name not in self.rules:
            raise KeyError(name)
        if not rule.name.strip():
            raise ValueError("rule name cannot be empty")
        if rule.name != name and rule.name in self.rules:
            raise ValueError("rule name must be unique")
        self.rules.pop(name)
        self._evaluators.pop(name, None)
        self.history = [item for item in self.history if item.rule_name != name]
        self.add(rule)

    def remove(self, name: str) -> None:
        self.rules.pop(name, None)
        self._evaluators.pop(name, None)
        self.history = [item for item in self.history if item.rule_name != name]

    def set_test_mode(self, name: str, enabled: bool) -> None:
        if name not in self.rules:
            raise KeyError(name)
        self.rules[name].test_mode = enabled

    def duplicate(self, name: str, new_name: str) -> None:
        if name not in self.rules:
            raise KeyError(name)
        if not new_name.strip() or new_name in self.rules:
            raise ValueError("new rule name must be unique and non-empty")
        import copy
        rule = copy.deepcopy(self.rules[name])
        rule.name = new_name
        rule.enabled = False
        self.add(rule)

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name not in self.rules:
            raise KeyError(name)
        self.rules[name].enabled = enabled
        if not enabled:
            self._evaluators[name].state = False
            self._evaluators[name]._candidate_since = None

    def test(self, rule: DmxRule, values: list[int] | bytes, now: float | None = None) -> RuleEvaluation:
        """Evaluate a rule against a snapshot without mutating its live evaluator/history."""
        evaluator = DmxRuleEvaluator(rule)
        trace = evaluator.evaluate(values, now)
        return RuleEvaluation(rule.name, trace, None, False)

    def simulate(self, name: str, values: list[int] | bytes, now: float | None = None) -> RuleEvaluation:
        if name not in self.rules:
            raise KeyError(name)
        rule = self.rules[name]
        evaluator = self._evaluators[name]
        before = evaluator.state
        trace = evaluator.evaluate(values, now)
        transitioned = before != trace.active
        # Simulation/test never executes a Home Assistant service. It only proposes it.
        action = None
        if transitioned and rule.enabled and not rule.test_mode:
            action = rule.action if trace.active else rule.off_action
        result = RuleEvaluation(name, trace, action, transitioned)
        self.history.append(result)
        if len(self.history) > self.max_history:
            del self.history[:-self.max_history]
        return result

    def evaluate_snapshot(self, protocol: str, universe: int, source: str | None,
                          values: list[int] | bytes, now: float | None = None) -> list[RuleEvaluation]:
        results: list[RuleEvaluation] = []
        for name, rule in self.rules.items():
            if not rule.enabled or rule.universe != universe:
                continue
            if rule.source and rule.source != source and rule.source != protocol:
                continue
            results.append(self.simulate(name, values, now))
        return results

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name,
                "universe": r.universe,
                "source": r.source,
                "channels": list(r.condition.channels),
                "mode": r.condition.mode,
                "threshold_on": r.condition.threshold_on,
                "threshold_off": r.condition.threshold_off,
                "on_delay_ms": r.on_delay_ms,
                "off_delay_ms": r.off_delay_ms,
                "enabled": r.enabled,
                "test_mode": r.test_mode,
                "state": self._evaluators[name].state,
            }
            for name, r in self.rules.items()
        ]

    def trace_snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "rule": item.rule_name,
                "active": item.trace.active,
                "target": item.trace.target,
                "active_channels": list(item.trace.active_channels),
                "count_active": item.trace.count_active,
                "required": item.trace.required,
                "threshold": item.trace.threshold,
                "pending": item.trace.pending,
                "reason": item.trace.reason,
            }
            for item in self.history[-50:]
        ]
