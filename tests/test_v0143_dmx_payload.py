from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CC=ROOT/'custom_components/dmx_monitor'
def test_dmx_sensor_preserves_coordinator_payload():
    s=(CC/'sensor.py').read_text()
    assert 'packed = item.get("values_b64")' in s
    assert 'row["values_b64"] = packed' in s
def test_dmx_selector_stable_key_and_session_persistence():
    s=(CC/'static/show-network.js').read_text()
    assert "key:`obs:${u.protocol||''}:${u.universe||''}:${u.source||''}`" in s
    assert "show-network-dmx-selection" in s
