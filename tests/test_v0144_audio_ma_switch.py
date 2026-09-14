from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def test_v0144_wiring():
    assert '"version": "0.14.4"' in (ROOT/'custom_components/dmx_monitor/manifest.json').read_text()
    assert 'dante_fresh_sources' in (ROOT/'custom_components/dmx_monitor/dante.py').read_text()
    assert 'aes67_sessions' in (ROOT/'custom_components/dmx_monitor/aes67.py').read_text()
    assert 'OBJECT IDENTIFIER' in (ROOT/'custom_components/dmx_monitor/snmp.py').read_text()
    assert 'unknown_until_evidence' in (ROOT/'custom_components/dmx_monitor/ma_remote.py').read_text()
