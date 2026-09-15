from pathlib import Path
ROOT=Path(__file__).parents[1]
CC=ROOT/'custom_components/dmx_monitor'

def test_dmx_dynamic_entity_dedupes_protocol_universe():
    t=(CC/'coordinator.py').read_text()
    assert 'entity_key = (str(protocol).strip().lower(), int(universe))' in t
    assert 'self.dmx_universe_entity_callback(protocol, int(universe))' in t

def test_direct_dmx_universe_service_is_wired():
    assert 'set_dmx_universes:' in (CC/'services.yaml').read_text()
    assert '"set_dmx_universes"' in (CC/'services/configuration.py').read_text()
    assert "'set_dmx_universes'" in (CC/'static/show-network.js').read_text()

def test_ma_unknown_until_evidence():
    t=(CC/'ma_remote.py').read_text()
    assert 'station non classifiée' in t
    assert 'classification_policy' in t

def test_dante_known_dns_sd_types_are_browsed():
    t=(CC/'vendor_discovery.py').read_text()
    assert '_netaudio-arc._udp.local.' in t
    assert '_netaudio-dante._udp.local.' in t

def test_frontend_and_discovery_are_throttled():
    ui=(CC/'static/show-network.js').read_text()
    rt=(CC/'runtime/setup.py').read_text()
    assert 'setTimeout(run,750)' in ui
    assert 'timedelta(seconds=180)' in rt
