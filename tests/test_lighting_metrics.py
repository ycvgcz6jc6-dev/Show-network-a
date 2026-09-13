from custom_components.dmx_monitor.lighting_receiver import UniverseTracker

def test_sequence_loss_metric_and_interval():
    t=UniverseTracker(); t.observe('sACN',1,'10.0.0.1',bytes([1]),sequence=1); t._last_time[('sACN',1,'10.0.0.1')] -= .01
    x=t.observe('sACN',1,'10.0.0.1',bytes([1]),sequence=3)
    assert x.inter_arrival_ms > 0
    assert x.sequence_loss_pct > 0
