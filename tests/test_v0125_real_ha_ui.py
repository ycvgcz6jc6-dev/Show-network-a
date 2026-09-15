from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_projector_on_yaml_key_is_quoted():
    text=(ROOT/'custom_components/dmx_monitor/services.yaml').read_text()
    block=text.split('projector_power:',1)[1].split('projector_input:',1)[0]
    assert '    "on":' in block
    assert '\n    on:\n' not in block

def test_panel_buttons_are_wired_and_security_ui_present():
    text=(ROOT/'custom_components/dmx_monitor/static/show-network.js').read_text()
    for token in ["#classic","#timeline","#archive","set_security_password","unlock_security","lock_security","config/entity_registry/list"]:
        assert token in text

def test_enttec_receive_switch_has_no_security_gate():
    text=(ROOT/'custom_components/dmx_monitor/switch.py').read_text()
    block=text.split('class EnttecListenSwitch',1)[1].split('class ProjectorControlSwitch',1)[0]
    assert 'require_unlocked' not in block
