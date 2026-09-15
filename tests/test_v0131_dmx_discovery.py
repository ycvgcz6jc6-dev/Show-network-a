from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_collection_sensor_states_are_scalar_and_payloads_are_attributes():
    text = (ROOT / "custom_components/dmx_monitor/sensor.py").read_text()
    assert 'if isinstance(value, (list, tuple, set, dict)):' in text
    assert 'return len(value)' in text
    assert 'if self._key == "etc_sensor_catalog":' in text
    assert 'return {"sensors": self.coordinator.data.get("etc_sensor_catalog", [])}' in text
    assert '("discovery_status", "État découverte / Discovery status", None)' in text


def test_dmx_module_is_not_rebuilt_on_every_hass_update():
    text = (ROOT / "custom_components/dmx_monitor/static/show-network.js").read_text()
    assert "if(this._view.startsWith('module:'))" in text
    assert "#module-content > *" in text
    assert "el.hass=this._hass" in text
    assert "sel?.addEventListener('change'" in text
    assert "this.selectionKey=e.target.value" in text


def test_discovery_merges_generic_mdns_arp_and_passive_protocol_sources():
    vendor = (ROOT / "custom_components/dmx_monitor/vendor_discovery.py").read_text()
    runtime = (ROOT / "custom_components/dmx_monitor/runtime/setup.py").read_text()
    coordinator = (ROOT / "custom_components/dmx_monitor/coordinator.py").read_text()
    pipeline = (ROOT / "custom_components/dmx_monitor/discovery_pipeline.py").read_text()
    assert 'if not vendor:' not in vendor
    assert '"properties": props' in vendor
    assert 'arp_neighbors' in runtime
    assert '"arp_neighbors"' in runtime
    assert 'sources={"arp_cache"}' in runtime
    assert 'sources={"dmx_passive"}' in coordinator
    assert 'sources={"ma_net3_passive"}' in coordinator
    assert 'protocol = fp.protocol or (f"mDNS:' in pipeline


def test_discovery_ui_exposes_real_method_counts_and_errors():
    text = (ROOT / "custom_components/dmx_monitor/static/show-network.js").read_text()
    assert "mDNS ${ds.mdns_services??0}" in text
    assert "ARP ${ds.arp_neighbors??0}" in text
    assert "(ds.errors||[]).join(' | ')" in text
    assert "Aucun équipement observé" in text


def test_version_0131():
    manifest = (ROOT / "custom_components/dmx_monitor/manifest.json").read_text()
    const = (ROOT / "custom_components/dmx_monitor/const.py").read_text()
    init = (ROOT / "custom_components/dmx_monitor/__init__.py").read_text()
    assert '"version": "0.15.2"' in manifest
    assert 'VERSION = "0.15.2"' in const
    assert 'show-network.js?v=0.15.2' in init
