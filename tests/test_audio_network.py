from custom_components.dmx_monitor.audio_health import AudioHealth
from custom_components.dmx_monitor.network_health import NetworkHealth

def test_audio_health_empty_is_safe():
    s=AudioHealth().snapshot(None,None,None,None,None)
    assert 'audio_health' in s

def test_network_health_tracks_protocol():
    n=NetworkHealth(); n.observe_packet('eth0','sACN'); s=n.snapshot()
    assert s['packets_observed'] >= 1
