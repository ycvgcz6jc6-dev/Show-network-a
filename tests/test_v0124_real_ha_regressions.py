from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "dmx_monitor"


def test_options_flow_does_not_assign_config_entry():
    text = (COMP / "config_flow.py").read_text()
    assert "self.config_entry = config_entry" not in text
    assert "return DmxMonitorOptionsFlow()" in text


def test_discovery_uses_ha_shared_zeroconf():
    vendor = (COMP / "vendor_discovery.py").read_text()
    punch = (COMP / "punchlight_network.py").read_text()
    for text in (vendor, punch):
        assert "ha_zeroconf.async_get_instance(hass)" in text
        assert "Zeroconf(" not in text
        assert ".close()" not in text


def test_sidebar_panel_is_registered():
    init = (COMP / "__init__.py").read_text()
    assert "panel_custom.async_register_panel" in init
    assert 'frontend_url_path="show-network"' in init
    assert 'webcomponent_name="show-network-pro-dashboard"' in init
