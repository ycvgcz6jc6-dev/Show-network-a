"""Tests for rules.py's DMX rule engine (DmxCondition, DmxRuleEvaluator,
RuleSet, parse_channel_selection). No test previously existed for this
module. Behaviours below were first verified by running the real code
interactively (hysteresis threshold_on/threshold_off, channel-range
parsing) before being written down as fixed regression assertions.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor.rules import (
    DmxCondition, DmxRule, DmxAction, DmxRuleEvaluator, RuleSet,
    parse_channel_selection,
)


# --- DmxCondition validation ---------------------------------------------

def test_condition_rejects_invalid_mode():
    with pytest.raises(ValueError):
        DmxCondition(channels=(1,), mode="bogus")


def test_condition_rejects_out_of_range_channel():
    with pytest.raises(ValueError):
        DmxCondition(channels=(0,))
    with pytest.raises(ValueError):
        DmxCondition(channels=(513,))


def test_condition_rejects_out_of_range_threshold():
    with pytest.raises(ValueError):
        DmxCondition(channels=(1,), threshold_on=256)
    with pytest.raises(ValueError):
        DmxCondition(channels=(1,), threshold_off=-1)


def test_condition_x_of_y_must_fit_channel_count():
    with pytest.raises(ValueError):
        DmxCondition(channels=(1, 2), mode="x_of_y", x=3)
    DmxCondition(channels=(1, 2), mode="x_of_y", x=2)  # must not raise


# --- parse_channel_selection ----------------------------------------------

def test_parse_channel_selection_range_and_list_and_bracket_forms():
    assert parse_channel_selection("1,2,5-8") == (1, 2, 5, 6, 7, 8)
    assert parse_channel_selection([1, 2, 3]) == (1, 2, 3)
    assert parse_channel_selection("[1, 2, 3]") == (1, 2, 3)


def test_parse_channel_selection_deduplicates_and_sorts():
    assert parse_channel_selection("5,1,5,3-4") == (1, 3, 4, 5)


def test_parse_channel_selection_rejects_out_of_range():
    with pytest.raises(ValueError):
        parse_channel_selection("0")
    with pytest.raises(ValueError):
        parse_channel_selection("513")


def test_parse_channel_selection_rejects_empty():
    with pytest.raises(ValueError):
        parse_channel_selection("")
    with pytest.raises(ValueError):
        parse_channel_selection([])


def test_parse_channel_selection_rejects_malformed_text():
    with pytest.raises(ValueError):
        parse_channel_selection("abc")
    with pytest.raises(ValueError):
        parse_channel_selection("-5")


# --- DmxRuleEvaluator: threshold hysteresis --------------------------------

def _evaluator(threshold_on=200, threshold_off=100, mode="any", channels=(1,), x=1, on_delay_ms=0, off_delay_ms=0):
    cond = DmxCondition(channels=channels, mode=mode, threshold_on=threshold_on, threshold_off=threshold_off, x=x)
    rule = DmxRule(name="test", universe=1, condition=cond, on_delay_ms=on_delay_ms, off_delay_ms=off_delay_ms)
    return DmxRuleEvaluator(rule)


def test_below_threshold_on_stays_inactive():
    ev = _evaluator()
    trace = ev.evaluate([150])
    assert trace.active is False


def test_at_threshold_on_activates_inclusive():
    ev = _evaluator()
    trace = ev.evaluate([200])
    assert trace.active is True


def test_hysteresis_stays_active_between_the_two_thresholds():
    """Once ON, a value between threshold_off (100) and threshold_on
    (200) must not turn it back off -- that's the entire point of having
    two separate thresholds instead of one."""
    ev = _evaluator()
    ev.evaluate([200])  # turn on
    trace = ev.evaluate([150])
    assert trace.active is True


def test_hysteresis_deactivates_at_threshold_off_inclusive():
    ev = _evaluator()
    ev.evaluate([200])  # turn on
    trace = ev.evaluate([100])
    assert trace.active is False


def test_no_distinct_threshold_off_uses_threshold_on_both_ways():
    """threshold_off=None (the default) means both directions use the
    same threshold_on value -- no hysteresis band."""
    ev = _evaluator(threshold_on=128, threshold_off=None)
    ev.evaluate([128])
    assert ev.state is True
    trace = ev.evaluate([127])
    assert trace.active is False


# --- DmxRuleEvaluator: any / all / x_of_y modes ---------------------------

def test_mode_any_activates_with_one_channel_above_threshold():
    ev = _evaluator(mode="any", channels=(1, 2, 3), threshold_on=100, threshold_off=100)
    trace = ev.evaluate([0, 150, 0])
    assert trace.active is True
    assert trace.count_active == 1


def test_mode_all_requires_every_channel_above_threshold():
    ev = _evaluator(mode="all", channels=(1, 2, 3), threshold_on=100, threshold_off=100)
    trace = ev.evaluate([150, 150, 50])
    assert trace.active is False
    trace2 = ev.evaluate([150, 150, 150])
    assert trace2.active is True


def test_mode_x_of_y_requires_exact_count():
    ev = _evaluator(mode="x_of_y", channels=(1, 2, 3, 4), x=2, threshold_on=100, threshold_off=100)
    trace = ev.evaluate([150, 0, 0, 0])  # only 1 of 4 above threshold
    assert trace.active is False
    trace2 = ev.evaluate([150, 150, 0, 0])  # exactly 2 of 4
    assert trace2.active is True


# --- DmxRuleEvaluator: on/off delay ----------------------------------------

def test_on_delay_holds_pending_until_elapsed():
    ev = _evaluator(on_delay_ms=1000)
    t0 = 1000.0
    trace1 = ev.evaluate([200], now=t0)
    assert trace1.active is False
    assert trace1.pending == "on"
    trace2 = ev.evaluate([200], now=t0 + 0.5)  # 500ms elapsed, not enough
    assert trace2.active is False
    assert trace2.pending == "on"
    trace3 = ev.evaluate([200], now=t0 + 1.0)  # 1000ms elapsed
    assert trace3.active is True
    assert trace3.pending is None


def test_on_delay_resets_if_condition_drops_before_elapsing():
    ev = _evaluator(on_delay_ms=1000)
    t0 = 1000.0
    ev.evaluate([200], now=t0)
    ev.evaluate([0], now=t0 + 0.5)  # condition no longer met -- cancels the pending activation
    trace = ev.evaluate([200], now=t0 + 0.6)  # re-triggered; delay must restart from here
    assert trace.pending == "on"
    trace2 = ev.evaluate([200], now=t0 + 1.0)  # only 400ms since re-trigger -- not enough yet
    assert trace2.active is False


def test_off_delay_independent_from_on_delay():
    ev = _evaluator(on_delay_ms=0, off_delay_ms=500, threshold_off=100)
    t0 = 1000.0
    ev.evaluate([200], now=t0)  # turns on immediately, no on_delay
    assert ev.state is True
    trace = ev.evaluate([0], now=t0 + 0.1)  # below threshold_off; candidate_since starts here
    assert trace.active is True
    assert trace.pending == "off"
    trace2 = ev.evaluate([0], now=t0 + 0.6)  # 500ms since candidate_since (t0+0.1), not since t0
    assert trace2.active is False


# --- RuleSet: add / update / remove / duplicate ----------------------------

def test_ruleset_add_rejects_empty_name():
    rs = RuleSet()
    with pytest.raises(ValueError):
        rs.add(DmxRule(name="  ", universe=1, condition=DmxCondition(channels=(1,))))


def test_ruleset_update_rejects_rename_collision():
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,))))
    rs.add(DmxRule(name="b", universe=1, condition=DmxCondition(channels=(1,))))
    with pytest.raises(ValueError):
        rs.update("a", DmxRule(name="b", universe=1, condition=DmxCondition(channels=(1,))))


def test_ruleset_update_unknown_name_raises_keyerror():
    rs = RuleSet()
    with pytest.raises(KeyError):
        rs.update("missing", DmxRule(name="x", universe=1, condition=DmxCondition(channels=(1,))))


def test_ruleset_duplicate_requires_unique_nonempty_name():
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,))))
    with pytest.raises(ValueError):
        rs.duplicate("a", "a")  # collides with itself
    with pytest.raises(ValueError):
        rs.duplicate("a", "")


def test_ruleset_duplicate_disables_the_copy():
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,)), enabled=True))
    rs.duplicate("a", "a-copy")
    assert rs.rules["a-copy"].enabled is False
    assert rs.rules["a"].enabled is True  # original untouched


def test_ruleset_set_enabled_false_resets_live_state():
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,), threshold_on=100), enabled=True))
    rs.simulate("a", [150])
    assert rs._evaluators["a"].state is True
    rs.set_enabled("a", False)
    assert rs._evaluators["a"].state is False


def test_ruleset_simulate_never_returns_action_in_test_mode():
    action = DmxAction(domain="light", service="turn_on")
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,), threshold_on=100),
                    action=action, enabled=True, test_mode=True))
    result = rs.simulate("a", [150])
    assert result.transitioned is True
    assert result.action_due is None  # test_mode must never propose a real action


def test_ruleset_simulate_proposes_action_when_enabled_and_not_test_mode():
    action = DmxAction(domain="light", service="turn_on")
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,), threshold_on=100),
                    action=action, enabled=True, test_mode=False))
    result = rs.simulate("a", [150])
    assert result.action_due is action


def test_ruleset_test_method_does_not_mutate_live_evaluator():
    """RuleSet.test() must evaluate against a scratch evaluator, leaving
    the rule's real running state (and history) untouched."""
    rs = RuleSet()
    rs.add(DmxRule(name="a", universe=1, condition=DmxCondition(channels=(1,), threshold_on=100), enabled=True))
    rs.test(rs.rules["a"], [150])
    assert rs._evaluators["a"].state is False  # untouched by test()
    assert rs.history == []
