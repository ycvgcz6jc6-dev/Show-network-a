from pathlib import Path
from custom_components.dmx_monitor.snmp import _tlv, _oid, parse_response, _int
from custom_components.dmx_monitor.device_fingerprints import fingerprint_mac
from custom_components.dmx_monitor.dmx_circuit_monitor import DmxCircuitMonitor

ROOT=Path(__file__).parents[1]
COMP=ROOT/'custom_components'/'dmx_monitor'

def test_luminex_mac_prefix_is_evidence():
    assert fingerprint_mac('D0:69:9E:00:11:22').vendor == 'Luminex'
    assert fingerprint_mac('00:50:C2:9C:91:23').vendor == 'Luminex'

def test_snmp_parser_decodes_object_identifier():
    rid=123
    vb=_tlv(0x30,_oid('1.3.6.1.2.1.1.2.0')+_oid('1.3.6.1.4.1.4413.1'))
    pdu=_tlv(0xa2,_int(rid)+_int(0)+_int(0)+_tlv(0x30,vb))
    msg=_tlv(0x30,_tlv(0x02,b'\x00')+_tlv(0x04,b'Public')+pdu)
    assert parse_response(msg,rid) == '1.3.6.1.4.1.4413.1'

def test_circuit_monitor_is_receive_only_and_reports_group(tmp_path):
    m=DmxCircuitMonitor(tmp_path/'c.json')
    m.upsert({'name':'Alims','protocol':'sACN','universe':1,'circuits':[{'channel':1,'on_threshold':128,'off_threshold':10}]})
    m.observe('sACN',1,'192.0.2.1',bytes([255])+bytes(511))
    snap=m.snapshot(); assert snap['dmx_circuit_groups'][0]['state']=='on'

def test_ui_separates_rule_watchdog_circuit_and_power_and_persists_details():
    text=(COMP/'static'/'show-network.js').read_text()
    for token in ('Rule Builder','Signal Watchdogs','DMX Circuit Monitor','Power Manager','snCaptureDetails','data-persist="dante-geek"','Auto','Surveiller','Ignorer'):
        assert token in text
    assert 'prompt(' not in text

def test_logo_assets_are_real_pngs():
    for name in ('show-network-logo.png','show-network-icon.png'):
        data=(COMP/'static'/'assets'/name).read_bytes(); assert data.startswith(b'\x89PNG')

def test_power_sacn_roundtrips_through_receive_parser():
    from custom_components.dmx_monitor.power_manager import build_sacn_frame
    from custom_components.dmx_monitor.lighting_receiver import parse_sacn_dmp
    values=bytes([0,1,2,255])+bytes(508)
    parsed=parse_sacn_dmp(build_sacn_frame(123,values,sequence=9,priority=110))
    assert parsed and parsed[0]==123 and parsed[3]==values and parsed[2]==9 and parsed[1]==110
