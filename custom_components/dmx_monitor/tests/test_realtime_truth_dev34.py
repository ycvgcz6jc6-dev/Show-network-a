import time
from custom_components.dmx_monitor.audio_health import AudioHealth
from custom_components.dmx_monitor.audio_ptp import PTPMonitor
from custom_components.dmx_monitor.ma_remote import MARemoteInventory
from custom_components.dmx_monitor.punchlight import PunchLightState


def test_ptp_stale_grandmaster_is_history_not_active():
    m=PTPMonitor()
    m.last_grandmaster_identity='0011223344556677'
    m.grandmaster_last_seen=time.time()-10
    snap=m.snapshot()
    assert snap['ptp_grandmaster_identity']=='0011223344556677'
    assert snap['ptp_active_grandmaster_identity'] is None
    assert snap['ptp_grandmaster_fresh'] is False
    health=AudioHealth().snapshot(ptp=snap)
    assert health['audio_network_health']['clock']['leader_identity'] is None
    assert health['audio_network_health']['clock']['last_leader_identity']=='0011223344556677'


def test_ma_sessions_distinguish_historical_from_live():
    inv=MARemoteInventory()
    inv.observe('10.0.0.1','239.195.0.1',session_index=1,observed_at=1.0)
    snap=inv.snapshot()
    assert snap['session_count']==1
    assert snap['active_session_count']==0
    assert snap['sessions'][0]['state']=='STALE'
    assert snap['sessions'][0]['live_member_count']==0


def test_punchlight_snapshot_marks_error_unhealthy():
    state=PunchLightState('MIDI Port', lambda _: None)
    state._port=object()
    state.last_error='device disconnected'
    snap=state.snapshot()
    assert snap['connected'] is True
    assert snap['healthy'] is False
