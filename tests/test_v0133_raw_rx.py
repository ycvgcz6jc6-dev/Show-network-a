from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
CC = ROOT / "custom_components" / "dmx_monitor"


def test_version_bumped():
    assert '"version": "0.14.4"' in (CC / "manifest.json").read_text()
    assert 'VERSION = "0.14.4"' in (CC / "const.py").read_text()


def test_sacn_multicast_address_is_e131_universe_address():
    text = (CC / "lighting_receiver.py").read_text()
    assert 'int(universe) // 256' in text
    assert 'int(universe) % 256' in text
    assert '(int(universe) - 1)' not in text


def test_sacn_binds_wildcard_and_joins_selected_interface():
    text = (CC / "lighting_receiver.py").read_text()
    assert 'bind_host = "0.0.0.0" if protocol == "SACN" else self.interface' in text
    assert '"membership_interface": self.interface' in text
    assert '"configured_groups"' in text


def test_ma_raw_sources_and_packet_signature_are_exposed():
    text = (CC / "ma_net3_listener.py").read_text()
    for token in ('last_packet_prefix_hex', 'last_packet_prefix_ascii', 'source_stats', '"raw_sources"'):
        assert token in text


def test_fixture_catalog_is_preloaded_off_event_loop():
    fp = (CC / "fixture_profiles.py").read_text()
    setup = (CC / "runtime" / "setup.py").read_text()
    assert '_RAW=load_yaml_catalog' not in fp
    assert 'def load_profiles()' in fp
    assert 'await hass.async_add_executor_job(load_profiles)' in setup


def test_frontend_renders_sacn_groups_and_ma_raw_sources():
    text = (CC / "static" / "show-network.js").read_text()
    for token in ('Interface multicast', 'Raw packet', 'Raw source', 'last_packet_prefix_hex'):
        assert token in text
