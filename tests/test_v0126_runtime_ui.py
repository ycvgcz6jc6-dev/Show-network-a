from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "dmx_monitor"

def test_action_dispatcher_is_background_task():
    text=(COMP/"ha/action_dispatcher.py").read_text()
    assert "async_create_background_task" in text
    assert "async_create_task(self._run()" not in text

def test_initial_vendor_discovery_is_background_task():
    text=(COMP/"runtime/setup.py").read_text()
    assert "async_create_background_task(_vendor_discovery_tick()" in text

def test_full_module_navigation_is_exposed():
    text=(COMP/"static/show-network.js").read_text()
    for token in ["DMX / Art-Net / sACN","DMX → Home Assistant","OSC / MIDI / PunchLight","Rule Builder","Audio / Dante / AES67","Vidéo / Projecteurs","grandMA3 / MA-Net3","Inventaire / Découverte","HA Builder","Constructeurs","Diagnostics / Reliability","Configuration générale HA"]:
        assert token in text
    for tag in ["dmx-monitor-panel","dmx-live-view","enttec-panel","dmx-ha-zones-panel","dmx-ha-mapping-panel","osc-learn-panel","osc-mapping-panel","show-network-rule-builder","show-network-topology-panel","ma-inspector-panel","show-network-inventory","show-network-ha-builder-panel","show-network-brand-catalog","show-network-reliability-panel"]:
        assert tag in text

def test_security_ui_handles_home_assistant_boolean_state_strings():
    text=(COMP/"static/show-network.js").read_text()
    assert "_truthy(v)" in text
    assert "CONFIGURÉ — VERROUILLÉ" in text
    assert "sec-submit" in text
    assert "prompt(" not in text
    assert "Commandes actives déverrouillées" in text

def test_options_flow_does_not_construct_unmanaged_config_flow():
    text=(COMP/"config_flow.py").read_text()
    block=text.split("class DmxMonitorOptionsFlow",1)[1]
    assert "DmxMonitorConfigFlow()" not in block
    assert "_choices_for_hass(self.hass)" in block
    assert "_schema_for_hass(self.hass" in block

def test_projector_on_key_remains_quoted():
    text=(COMP/"services.yaml").read_text()
    block=text.split("projector_power:",1)[1].split("projector_input:",1)[0]
    assert '    "on":' in block
