from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSOR = (ROOT / 'custom_components/dmx_monitor/sensor.py').read_text()
JS = (ROOT / 'custom_components/dmx_monitor/static/show-network.js').read_text()


def test_sensor_catalog_tuple_contract_accepts_unit():
    assert 'def __init__(self, coordinator, key, name, unit=None):' in SENSOR
    assert 'self._declared_unit = unit' in SENSOR


def test_sensor_attributes_feed_real_panels():
    assert '"mappings": self.coordinator.data.get("dmx_ha_mappings", [])' in SENSOR
    assert '"topology": self.coordinator.data.get("topology", {"nodes": [], "links": []})' in SENSOR
    assert 'if self._key == "journal_archive":' in SENSOR
    assert 'return dict(self.coordinator.data.get("archive", {}))' in SENSOR


def test_network_capacity_specific_cases_precede_generic_network_branch():
    assert SENSOR.index('if self._key == "network_capacity_utilization"') < SENSOR.index('if self._key.startswith("network_")')


def test_fake_dmx_live_removed():
    assert 'class DmxLiveView' not in JS
    assert "'dmx-live-view'" not in JS
    assert 'Math.floor((i*7)%256)' not in JS
    assert 'données observées réelles' in JS


def test_dmx_monitor_distinguishes_streams_and_configured_universes():
    assert 'configured_universes' in SENSOR
    assert "protocol||''" in JS and "source||''" in JS
    assert 'configuré · aucun trafic' in JS
    assert "isLive=Boolean(current?.observed&&this.rate>0)" in JS


def test_network_config_does_not_invent_disabled_state_when_sensor_missing():
    assert "État indisponible" in JS
    assert "aucun état activé/désactivé n'est supposé" in JS
