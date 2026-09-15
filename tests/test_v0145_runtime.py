import importlib.util
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/"custom_components"/"dmx_monitor"

def load(name, rel):
    spec=importlib.util.spec_from_file_location(name, BASE/rel)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def test_ma_session_groups_official_mapping():
    m=load("ma_net3_listener_test","ma_net3_listener.py")
    assert m.session_groups(0,"236.4.1") == ("236.4.1.1","236.4.1.2","236.4.1.3","236.4.1.4")
    assert m.session_groups(3,"236.4.1") == ("236.4.1.13","236.4.1.14","236.4.1.15","236.4.1.16")
    assert m.session_groups(31,"239.4.1")[-1] == "239.4.1.128"

def test_ma_remote_builds_session_only_from_group_evidence():
    m=load("ma_remote_test","ma_remote.py")
    inv=m.MARemoteInventory(); inv.observe("10.0.0.10","session:2",session_index=2); inv.observe("10.0.0.11","session:2",session_index=2)
    s=inv.snapshot(); assert s["session_count"]==1; assert s["sessions"][0]["session_index"]==2; assert s["sessions"][0]["member_count"]==2

def test_aes67_sdp_minimal_parse():
    m=load("aes67_test","aes67.py")
    pkt=b"SAP\x00application/sdp\x00v=0\r\no=- 1 1 IN IP4 10.0.0.2\r\ns=Test AES67\r\nc=IN IP4 239.69.1.1/32\r\nm=audio 5004 RTP/AVP 96\r\na=rtpmap:96 L24/48000/2\r\na=ts-refclk:ptp=IEEE1588-2008:00-00-00-00-00-00-00-01:0\r\n"
    parsed=m.AES67Monitor._parse_sdp(pkt,"10.0.0.2",123.0)
    assert parsed is not None
    _, row=parsed
    assert row["name"]=="Test AES67" and row["destination"]=="239.69.1.1" and row["port"]==5004

def test_ptp_header_version_split():
    m=load("ptp_test","audio_ptp.py")
    data=bytearray(64); data[0]=11; data[1]=2; data[4]=0
    assert m.PTPMonitor._decode_header(bytes(data)) == (11,2,0)
    data[1]=1
    assert m.PTPMonitor._decode_header(bytes(data))[1] == 1
