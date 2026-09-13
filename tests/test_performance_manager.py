from custom_components.dmx_monitor.performance_manager import AdaptivePerformance


def test_auto_profile_has_safe_levels():
    manager = AdaptivePerformance("auto")
    assert manager.decide(20, 30).level == "normal"
    assert manager.decide(55, 40).level == "optimized"
    assert manager.decide(72, 40).level == "economy"
    assert manager.decide(90, 40).level == "protection"


def test_auto_uses_memory_pressure_too():
    decision = AdaptivePerformance("auto").decide(30, 90)
    assert decision.level == "protection"
    assert decision.discovery_enabled is False


def test_fixed_minimal_is_documented_baseline():
    decision = AdaptivePerformance("minimal").decide(10, 10)
    assert decision.level == "minimal"
    assert decision.telemetry_interval_s == 10.0


def test_invalid_profile_falls_back_to_normal():
    assert AdaptivePerformance("unknown").decide(10, 10).level == "normal"
