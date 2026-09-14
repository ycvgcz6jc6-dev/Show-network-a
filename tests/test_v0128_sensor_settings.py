from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sensor_catalog_constructor_accepts_unit():
    text = (ROOT / "custom_components/dmx_monitor/sensor.py").read_text()
    assert "def __init__(self, coordinator, key, name, unit=None):" in text
    assert "self._declared_unit = unit" in text
    assert "ShowNetworkSensor(coordinator, *item)" in text


def test_sidebar_panel_does_not_hijack_integration_config():
    text = (ROOT / "custom_components/dmx_monitor/__init__.py").read_text()
    assert 'frontend_url_path="show-network"' in text
    assert "config_panel_domain=DOMAIN" not in text
    assert "show-network.js?v=0.14.8" in text


def test_version_0128():
    manifest = (ROOT / "custom_components/dmx_monitor/manifest.json").read_text()
    const = (ROOT / "custom_components/dmx_monitor/const.py").read_text()
    assert '"version": "0.14.8"' in manifest
    assert 'VERSION = "0.14.8"' in const
