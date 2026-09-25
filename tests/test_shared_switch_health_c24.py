"""Phase C24 (rapport maître, bloc Observabilité: "santé commune Pre-Show/
Doctor/Incident"). Audit-confirmed drift: doctor.py and pre_show.py each
independently computed switch-port-utilization thresholds and had
quietly diverged -- Doctor flagged 70%+ as "warning" (escalating to
"error" at 85%), Pre-Show only ever checked the single 85% threshold
with no warning tier. A port at 75% utilization was visible in Doctor
but invisible to Pre-Show's readiness check -- same underlying fact,
two different answers. health_engine.py, despite being the stated
"cross-protocol health correlation" engine, had no switch-utilization
check at all.

Fixed by extracting one shared calculation
(find_high_utilization_switch_ports) that all three now call, rather
than picking a "winning" threshold and copying it -- copying would
only recreate the same drift risk.
"""
from __future__ import annotations

from custom_components.dmx_monitor.health_engine import (
    ShowNetworkHealthEngine, find_high_utilization_switch_ports,
    SWITCH_UTIL_WARNING_PCT, SWITCH_UTIL_ERROR_PCT,
)
from custom_components.dmx_monitor.doctor import ShowNetworkDoctor
from custom_components.dmx_monitor.pre_show import PreShowCheck


def _switches(pct: float) -> list[dict]:
    """One switch, one port, at the given utilization percentage of a
    1000 Mbps link."""
    return [{
        "name": "Backstage GigaCore", "ip": "10.4.1.3",
        "ports": [{"index": 1, "name": "P1", "speed_mbps": 1000, "rx_mbps": pct * 10, "tx_mbps": 0}],
    }]


# --- The shared calculation itself ------------------------------------------

def test_below_warning_threshold_is_not_flagged():
    assert find_high_utilization_switch_ports(_switches(50.0)) == []


def test_at_warning_threshold_is_flagged_as_warning():
    result = find_high_utilization_switch_ports(_switches(70.0))
    assert len(result) == 1
    assert result[0]["severity"] == "warning"


def test_between_warning_and_error_is_still_warning_not_error():
    result = find_high_utilization_switch_ports(_switches(75.0))
    assert result[0]["severity"] == "warning"


def test_at_error_threshold_escalates_to_error():
    result = find_high_utilization_switch_ports(_switches(85.0))
    assert result[0]["severity"] == "error"


def test_picks_the_higher_of_rx_or_tx():
    switches = [{
        "name": "SW1", "ports": [{"index": 1, "speed_mbps": 1000, "rx_mbps": 900, "tx_mbps": 100}],
    }]
    result = find_high_utilization_switch_ports(switches)
    assert result[0]["direction"] == "rx_mbps"
    assert result[0]["utilization_pct"] == 90.0


def test_port_with_no_speed_is_skipped_not_a_crash():
    switches = [{"name": "SW1", "ports": [{"index": 1, "rx_mbps": 900}]}]  # no speed_mbps
    assert find_high_utilization_switch_ports(switches) == []


# --- Doctor and Pre-Show now agree on the same underlying fact -------------

def test_doctor_and_pre_show_agree_a_75_percent_port_is_not_critical():
    """The exact scenario the audit caught: 75% was 'warning' in Doctor
    and completely invisible in Pre-Show. Now: Doctor still reports it
    as a warning (not silently hidden), and Pre-Show -- whose readiness
    gate only cares about the error tier -- correctly still passes,
    using the *same* calculation Doctor used to reach its answer, not a
    second, independently-drifting one."""
    data = {"switch_telemetry": _switches(75.0)}

    doctor_result = ShowNetworkDoctor().run(data)
    bandwidth_check = next(c for c in doctor_result["checks"] if c["id"] == "audio_bandwidth")
    assert bandwidth_check["status"] == "warning"
    assert bandwidth_check["evidence"]["ports"][0]["utilization_pct"] == 75.0

    preshow_result = PreShowCheck().run(data)
    network_check = next(c for c in preshow_result["checks"] if c["id"] == "network")
    assert network_check["status"] == "pass"  # 75% is below Pre-Show's error-only gate


def test_doctor_and_pre_show_agree_an_85_percent_port_is_critical_in_both():
    data = {"switch_telemetry": _switches(90.0)}

    doctor_result = ShowNetworkDoctor().run(data)
    bandwidth_check = next(c for c in doctor_result["checks"] if c["id"] == "audio_bandwidth")
    assert bandwidth_check["status"] == "error"

    preshow_result = PreShowCheck().run(data)
    network_check = next(c for c in preshow_result["checks"] if c["id"] == "network")
    assert network_check["status"] == "fail"
    assert preshow_result["state"] == "NOT_READY"


def test_doctor_and_health_engine_report_the_same_port_facts():
    """health_engine.py had no switch-utilization check at all before
    this fix -- confirms it now reports the identical underlying figures
    Doctor does, for the same input."""
    data = {"switch_telemetry": _switches(90.0)}

    doctor_result = ShowNetworkDoctor().run(data)
    doctor_ports = next(c for c in doctor_result["checks"] if c["id"] == "audio_bandwidth")["evidence"]["ports"]

    engine_result = ShowNetworkHealthEngine().run(data)
    engine_check = next(c for c in engine_result["checks"] if c["key"] == "network.port_utilization")
    assert engine_check["status"] == "error"
    assert engine_check["evidence"]["ports"][0]["utilization_pct"] == doctor_ports[0]["utilization_pct"]


def test_health_engine_omits_the_check_entirely_when_nothing_is_high():
    """No noise when everything is quiet -- matches this engine's own
    'report observations, never manufacture a check with nothing to
    say' style used by its other _xxx() methods."""
    data = {"switch_telemetry": _switches(10.0)}
    result = ShowNetworkHealthEngine().run(data)
    assert not any(c["key"] == "network.port_utilization" for c in result["checks"])


def test_thresholds_are_the_same_named_constants_everywhere():
    """Guards against the exact failure mode that caused the original
    drift: a future edit changing one copy of '70' or '85' without
    touching the others. There is now only one copy to change."""
    assert SWITCH_UTIL_WARNING_PCT == 70.0
    assert SWITCH_UTIL_ERROR_PCT == 85.0
