from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CC=ROOT/"custom_components"/"dmx_monitor"

def test_version_and_cache():
    assert '"version": "0.14.4"' in (CC/"manifest.json").read_text()
    assert 'VERSION = "0.14.4"' in (CC/"const.py").read_text()
    assert 'show-network.js?v=0.14.4' in (CC/"__init__.py").read_text()

def test_dmx_values_reach_frontend():
    text=(CC/"coordinator.py").read_text()
    assert 'values_b64' in text
    assert 'base64.b64encode(item.values)' in text

def test_module_gates_and_projector_gate():
    cfg=(CC/"services"/"configuration.py").read_text()
    for name in ('artnet','sacn','ma_net3','osc_input','midi_input','punchlight','watchdog','ha_builder','diagnostics','projector_monitor'):
        assert f'"{name}"' in cfg
    flow=(CC/"config_flow.py").read_text()
    assert 'CONF_PROJECTOR_MONITOR_ENABLED' in flow
    assert 'CONF_CHAOS_ENABLED' in flow
    assert 'CONF_OSC_INPUT_INTERFACE' in flow

def test_osc_learn_is_wired():
    runtime=(CC/"runtime"/"setup.py").read_text()
    services=(CC/"services"/"osc.py").read_text()
    sensor=(CC/"sensor.py").read_text()
    js=(CC/"static"/"show-network.js").read_text()
    assert 'learn=coordinator.osc_learn' in runtime
    assert 'start_osc_learn' in services and 'stop_osc_learn' in services and 'clear_osc_learn' in services
    assert 'osc_learn' in sensor
    assert 'START LEARN' in js and 'Aucune ligne de démonstration' in js

def test_journal_recent_events_and_diagnostics_feedback():
    archive=(CC/"archive.py").read_text()
    js=(CC/"static"/"show-network.js").read_text()
    assert 'recent_events' in archive
    assert 'ÉVÉNEMENTS RÉCENTS' in js
    assert 'Activer les tests diagnostic' in js
    assert 'set_module_enabled' in js

def test_control_service_relative_imports_are_valid():
    text=(CC/"services"/"control.py").read_text()
    assert 'from ..osc_mapping import Mapping' in text
    assert 'from .osc_mapping import Mapping' not in text
