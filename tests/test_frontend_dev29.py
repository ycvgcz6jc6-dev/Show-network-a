from pathlib import Path

JS = Path("custom_components/dmx_monitor/static/show-network.js").read_text()

def test_security_draft_survives_rerender():
    assert "this._securityDraft.password=e.target.value" in JS
    assert "this._securityDraft.current=e.target.value" in JS
    assert "esc(d.password||'')" in JS

def test_regie_favorite_is_real_backend_mode():
    assert "data-star=" in JS
    assert "data-disc-star=" in JS
    assert "callService('dmx_monitor','set_device_override'" in JS
    assert "monitor_mode:mode" in JS
    assert "monitor_mode==='monitor'" in JS
    assert "monitor_mode==='watch'" not in JS
