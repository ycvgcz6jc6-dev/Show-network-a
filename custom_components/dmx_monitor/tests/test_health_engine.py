from custom_components.dmx_monitor.health_engine import ShowNetworkHealthEngine

def test_health_engine_detects_multiple_dmx_sources_and_loss():
    result = ShowNetworkHealthEngine().run({
        "network_interfaces": [{"name":"eth0"}],
        "dmx_universes": [
            {"protocol":"sACN","universe":1,"source":"10.0.0.1","sequence_loss_pct":0},
            {"protocol":"sACN","universe":1,"source":"10.0.0.2","sequence_loss_pct":2.5},
        ],
    })
    keys = {c["key"] for c in result["checks"]}
    assert result["overall"] == "warning"
    assert "dmx.multiple_sources" in keys
    assert "dmx.sequence_loss" in keys

def test_health_engine_does_not_invent_ptp_fault():
    result = ShowNetworkHealthEngine().run({"ptp_packets": 100, "ptp_sources": 2})
    keys = {c["key"] for c in result["checks"]}
    assert "ptp.activity" in keys
    assert "ptp.explicit_health" not in keys
