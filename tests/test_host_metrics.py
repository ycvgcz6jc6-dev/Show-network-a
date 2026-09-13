from custom_components.dmx_monitor.host_metrics import HostMetrics, snapshot


def test_host_metrics_snapshot_shape():
    value = snapshot()
    data = value.snapshot()
    assert 0 <= data["cpu_percent"] <= 100
    assert 0 <= data["memory_percent"] <= 100
    assert data["memory_used_bytes"] >= 0
    assert data["memory_total_bytes"] > 0


def test_host_metrics_is_immutable_contract():
    value = HostMetrics(12.5, 40.0, 100, 200)
    assert value.snapshot() == {
        "cpu_percent": 12.5,
        "memory_percent": 40.0,
        "memory_used_bytes": 100,
        "memory_total_bytes": 200,
    }
