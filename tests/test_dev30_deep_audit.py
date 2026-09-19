from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'custom_components/dmx_monitor/static/show-network.js').read_text(encoding='utf-8')
SETUP=(ROOT/'custom_components/dmx_monitor/runtime/setup.py').read_text(encoding='utf-8')
DEVICE=(ROOT/'custom_components/dmx_monitor/services/device.py').read_text(encoding='utf-8')
SERVICES=(ROOT/'custom_components/dmx_monitor/services.yaml').read_text(encoding='utf-8')

def test_manual_ip_favorite_is_real_service_chain():
    assert "register_manual_device" in SERVICES
    assert 'async_register(DOMAIN, "register_manual_device"' in DEVICE
    assert "callService('dmx_monitor','register_manual_device'" in JS
    assert "monitor_mode:'monitor'" in JS

def test_operator_ignore_does_not_blind_broad_discovery():
    assert 'state":"ignored"' not in SETUP
    assert 'monitor_mode","auto")=="ignore"' not in SETUP
    assert 'monitor_mode", "auto") == "ignore"' not in SETUP

def test_security_and_preshow_keep_drafts_during_live_refresh():
    assert "this._securityDraft.password=e.target.value" in JS
    assert "if(this.matches?.(':focus-within')){this._pending=true;return;}" in JS
