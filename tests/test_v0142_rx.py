import struct, time
from custom_components.dmx_monitor.lighting_receiver import parse_sacn_dmp
from custom_components.dmx_monitor.audio_ptp import PTPMonitor

def test_sacn_parser_extracts_512_slots():
    data=bytearray(638)
    data[0:2]=b'\x00\x10'; data[4:16]=b'ASC-E1.17\x00\x00\x00'
    data[108]=100; data[111]=7; struct.pack_into('>H',data,113,10)
    struct.pack_into('>H',data,123,513); data[125]=0
    data[126:638]=bytes([1])+bytes(511)
    u,p,s,v=parse_sacn_dmp(bytes(data))
    assert (u,p,s)==(10,100,7)
    assert len(v)==512 and v[0]==1

def test_ptp_clock_presence_snapshot():
    m=PTPMonitor('0.0.0.0')
    assert m.snapshot()['ptp_clock_present'] is False
    m.packets=1; m._last_time=time.time()
    assert m.snapshot()['ptp_clock_present'] is True
