from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CC = ROOT / "custom_components" / "dmx_monitor"


def test_version_bumped():
    assert '"version": "0.15.2"' in (CC / "manifest.json").read_text()
    assert 'VERSION = "0.15.2"' in (CC / "const.py").read_text()


def test_dmx_receiver_exposes_real_listener_diagnostics():
    text = (CC / "lighting_receiver.py").read_text()
    for token in (
        '"protocols": {', '"ARTNET": {', '"SACN": {',
        '"bound_endpoint"', '"packets_received"', '"packets_parsed"',
        '"last_source"', '"last_universe"', '"joined_groups"', '"join_errors"',
    ):
        assert token in text


def test_ma_listener_exposes_binding_and_multicast_diagnostics():
    text = (CC / "ma_net3_listener.py").read_text()
    for token in ('self.state = "starting"', 'self.bound_endpoint', 'self.joined_groups', 'self.join_errors', '"diagnostics": {'):
        assert token in text


def test_coordinator_publishes_protocol_rx_diagnostics():
    text = (CC / "coordinator.py").read_text()
    assert 'snapshot["protocol_rx_diagnostics"] = rx_diag' in text
    assert 'rx_diag["ma_net3"]' in text
    assert 'rx_diag["mdns"]' in text


def test_mdns_zero_is_diagnostic_not_silent():
    text = (CC / "runtime" / "setup.py").read_text()
    assert '"mdns_state": "scanning"' in text
    assert '"no_services_observed"' in text
    assert 'shared Zeroconf active; no mDNS service observed' in text


def test_frontend_renders_dmx_ma_and_mdns_diagnostics():
    text = (CC / "static" / "show-network.js").read_text()
    for token in ('Paquets reçus / parsés', 'Erreurs multicast', 'UDP listener', 'Multicast groups', 'mdns_detail'):
        assert token in text
