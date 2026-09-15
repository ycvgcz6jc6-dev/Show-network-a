"""CEM3 parser, network-policy, state and cancellation regression tests."""
import asyncio
from pathlib import Path
from time import time
from unittest.mock import AsyncMock
import xml.etree.ElementTree as ET
import pytest
from custom_components.dmx_monitor import etc_cem3 as cem

F = Path(__file__).parent/'fixtures/cem3'
DATA = {key: (F/name).read_text() for key, name in [('system','system.html'),('levels','levels.xml'),('properties','properties.xml'),('spaces','spaces.xml')]}


def monitor(monkeypatch, hosts=('10.2.2.3',), **kw):
    m = cem.CEM3WebMonitor(list(hosts), **kw)
    async def request(host, kind, source):
        return DATA[kind]
    m._request = AsyncMock(side_effect=request)
    monkeypatch.setattr(cem, 'selected_networks', lambda ips: [])
    return m


def test_real_72_circuit_fixtures():
    levels = cem.parse_cem3_levels(DATA['levels'])
    props = cem.parse_cem3_properties(DATA['properties'])
    assert len(levels) == len(props) == 72
    assert levels[0] == dict(udn=97,circuit=1,space=1,side='both',wsource='sACN',level=99,level_percent=99)
    assert props[48]['module_type']=='ETD25AFR'
    assert props[66]['module_type']=='ED15N'
    assert props[3]['control_mode']=='Dimmable'
    assert cem.parse_cem3_spaces(DATA['spaces'])[0]['active_preset']==0


@pytest.mark.parametrize('parser,body', [
 (cem.parse_cem3_levels,'<html/>'),
 (cem.parse_cem3_levels,DATA['levels'].replace('level="99"','level="999"')),
 (cem.parse_cem3_levels,DATA['levels'].replace('udn="98"','udn="97"')),
 (cem.parse_cem3_levels,DATA['levels'].replace('space="1"','space="-1"')),
 (cem.parse_cem3_levels,DATA['levels'].replace(' side="both"','')),
 (cem.parse_cem3_levels,'<!DOCTYPE a [<!ENTITY x "a">]><html/>'),
 (cem.parse_cem3_levels,'x'*(cem.MAX_BODY+1)),
 (cem.parse_cem3_properties,DATA['properties'].replace('threshold="50"','threshold="NaN"')),
 (cem.parse_cem3_spaces,DATA['spaces'].replace('active_sequence="0"','active_sequence="unknown"')),
])
def test_reject_bad_xml(parser,body):
    with pytest.raises((ValueError, ET.ParseError)):parser(body)


@pytest.mark.parametrize('body', ['rack dimmers','ETC CEM3','Sensor3','<script>ETC CEM3 Sensor3 Rack # 1</script>', DATA['system'].replace('ETC','ACME')])
def test_identity_rejects_false_positives(body):
    assert not cem.validate_cem3_identity(body)


def test_identity_and_system_values():
    assert cem.validate_cem3_identity(DATA['system'])
    d=cem.parse_cem3_system_html(DATA['system'])
    assert d['phase_x_voltage_v']==230 and d['cpu_temperature_c']==40
    assert d['software_version']=='3.2.0'
    assert cem.parse_cem3_system_html(DATA['system'].replace('40 C','104 F'))['cpu_temperature_c']==40


@pytest.mark.parametrize('host', ['example.com','http://10.2.2.3','10.2.2.3:80','0.0.0.0','224.1.2.3','255.255.255.255','::1'])
def test_hosts_are_literal_unicast_ipv4(host):
    with pytest.raises(ValueError): cem.CEM3WebMonitor([host])


@pytest.mark.asyncio
async def test_multi_rack_merge_and_throttle(monkeypatch):
    m=monitor(monkeypatch,hosts=('10.2.2.3','10.2.2.4'))
    await m.async_update()
    assert m.snapshot()['online']==2
    assert len(m.snapshot()['racks'][1]['dimmers']['circuits'])==72
    assert m.snapshot()['racks'][0]['dimmers']['circuits'][0]['module_type']=='ETD15AFR'
    assert 'circuits' not in m.snapshot(detail=False)['racks'][0]['dimmers']
    assert m._request.await_count==8
    await m.async_update(); assert m._request.await_count==8
    m._last_poll=float('-inf');await m.async_update()
    assert m._request.await_count==14  # properties cached for 60 seconds
    m.snapshot()['racks'][0]['dimmers']['circuits'].clear()
    assert len(m.snapshot()['racks'][0]['dimmers']['circuits'])==72
    await m.stop()


@pytest.mark.asyncio
async def test_offline_retains_data_but_never_fresh(monkeypatch):
    m=monitor(monkeypatch);await m.async_update()
    seen=m.racks['10.2.2.3'].last_seen_epoch
    m._request.side_effect=OSError('offline');m._last_poll=float('-inf')
    await m.async_update();s=m.snapshot()
    assert s['online']==0 and s['temperature_max_c'] is None
    assert s['racks'][0]['last_seen_epoch']==seen
    assert s['racks'][0]['dimmers']['circuits_total']==72
    assert not any(s['racks'][0]['freshness'].values())


@pytest.mark.asyncio
async def test_freshness_expires_without_poll(monkeypatch):
    m=monitor(monkeypatch);await m.async_update()
    for key in m.racks['10.2.2.3'].updated:m.racks['10.2.2.3'].updated[key]=time()-500
    assert not m.snapshot()['racks'][0]['fresh']
    assert m.snapshot()['online']==0


@pytest.mark.asyncio
async def test_partial_failure_preserves_properties_marks_stale(monkeypatch):
    m=monitor(monkeypatch);await m.async_update()
    m.racks['10.2.2.3'].updated['properties']=time()-61
    async def request(host,kind,source):
        if kind=='properties': raise OSError('unavailable')
        return DATA[kind]
    m._request.side_effect=request;m._last_poll=float('-inf');await m.async_update()
    row=m.snapshot()['racks'][0]
    assert row['online'] and row['freshness']['levels']
    assert not row['freshness']['properties']
    assert row['dimmers']['circuits'][0]['module_type']=='ETD15AFR'


@pytest.mark.asyncio
async def test_identity_failure_never_sends_post(monkeypatch):
    m=monitor(monkeypatch);m._request.side_effect=None;m._request.return_value='rack dimmers'
    await m.async_update()
    assert m._request.await_count==1
    assert not m.racks['10.2.2.3'].online


@pytest.mark.asyncio
async def test_properties_identity_mismatch(monkeypatch):
    m=monitor(monkeypatch)
    async def request(host,kind,source):
        return DATA[kind].replace('circuit="1"','circuit="100"') if kind=='properties' else DATA[kind]
    m._request.side_effect=request;await m.async_update()
    assert 'properties' in m.racks['10.2.2.3'].section_errors
    assert 'module_type' not in m.racks['10.2.2.3'].dimmers['circuits'][0]


def test_discovery_subnet_limits_neighbor_validation_and_interleaving():
    networks=[dict(address='10.1.0.1',network='10.1.0.0/30',interface='a'),dict(address='10.2.0.1',network='10.2.0.0/16',interface='b')]
    neighbors=[dict(ip='10.2.0.9',interface='b',complete=True),dict(ip='10.3.0.9',interface='b',complete=True),dict(ip='10.2.0.8',interface='a',complete=True),dict(ip='10.2.0.7',interface='b',complete=False)]
    assert cem.discovery_candidates(networks,neighbors)==[('10.1.0.2','10.1.0.1'),('10.2.0.9','10.2.0.1')]
    assert cem.discovery_candidates([networks[1]])==[]
    assert len(cem.discovery_candidates([dict(address='10.1.0.1',network='10.1.0.0/24',interface='a')]))==253


@pytest.mark.asyncio
async def test_selected_multi_nic_discovery_and_manual_routes(monkeypatch):
    m=monitor(monkeypatch,hosts=(),source_ips=['10.1.0.1','10.2.0.1'],discovery=True)
    rows=[dict(address=f'10.{i}.0.1',network=f'10.{i}.0.0/30',interface=str(i)) for i in (1,2)]
    monkeypatch.setattr(cem,'selected_networks',lambda ips:rows)
    await m.async_update()
    assert set(m.hosts)=={'10.1.0.2','10.2.0.2'}
    assert m.racks['10.1.0.2'].source_ip=='10.1.0.1'
    assert m.racks['10.2.0.2'].source_ip=='10.2.0.1'
    assert m._routes('10.3.0.2')==[]
    assert m._routes('10.1.0.2')==['10.1.0.1']


@pytest.mark.asyncio
async def test_discovery_without_selected_nic_never_scans(monkeypatch):
    m=monitor(monkeypatch,hosts=(),discovery=True);await m.async_update()
    m._request.assert_not_awaited()
    assert 'Select explicit' in m.discovery_status


@pytest.mark.asyncio
async def test_discovery_rejects_incomplete_rack(monkeypatch):
    m=monitor(monkeypatch,hosts=(),source_ips=['10.1.0.1'],discovery=True)
    monkeypatch.setattr(cem,'selected_networks',lambda ips:[dict(address='10.1.0.1',network='10.1.0.0/30',interface='a')])
    async def request(host,kind,source):return '<html/>' if kind=='properties' else DATA[kind]
    m._request.side_effect=request;await m.async_update();assert not m.hosts


@pytest.mark.asyncio
async def test_stop_cancels_inflight_poll_and_can_reload(monkeypatch):
    m=monitor(monkeypatch);entered=asyncio.Event()
    async def hang(*args):entered.set();await asyncio.sleep(60)
    m._request.side_effect=hang
    task=asyncio.create_task(m.async_update());await entered.wait()
    await m.stop();assert task.cancelled()
    assert not m._tasks and not m._sessions
    await m.async_update()
    replacement=monitor(monkeypatch);await replacement.async_update()
    assert replacement.snapshot()['online']==1
    await replacement.stop()

@pytest.mark.asyncio
async def test_discovery_batch_is_bounded_and_retries_are_delayed(monkeypatch):
    m=monitor(monkeypatch,hosts=(),source_ips=['10.1.0.1'],discovery=True)
    monkeypatch.setattr(cem,'selected_networks',lambda ips:[dict(address='10.1.0.1',network='10.1.0.0/24',interface='a')])
    m._request.side_effect=None;m._request.return_value='ordinary web page'
    await m.async_update();assert m._request.await_count==8
    assert len(m._candidates)==245
    await m.async_update();assert m._request.await_count==8
    m._candidates=[];m._last_poll=float('-inf');await m.async_update()
    assert m._request.await_count==8


@pytest.mark.asyncio
async def test_frame_system_uses_only_fixed_front_path(monkeypatch):
    m=monitor(monkeypatch)
    async def request(host,kind,source):
        if kind=='system':return '<html><iframe src="front.asp"></iframe></html>'
        if kind=='system_front':return DATA['system']
        return DATA[kind]
    m._request.side_effect=request;await m.async_update()
    assert m.snapshot()['online']==1
    assert [c.args[1] for c in m._request.await_args_list]==['system','system_front','levels','properties','spaces']


def test_rack_limit_and_manual_host_deduplication():
    assert cem.CEM3WebMonitor(['10.1.0.1','10.1.0.1']).hosts==('10.1.0.1',)
    with pytest.raises(ValueError):cem.CEM3WebMonitor([f'10.1.0.{i}' for i in range(1,34)])


@pytest.mark.asyncio
async def test_cached_properties_refresh_when_circuit_mapping_changes(monkeypatch):
    m=monitor(monkeypatch);await m.async_update()
    async def request(host,kind,source):return DATA[kind].replace('circuit="1"','circuit="100"')
    m._request.side_effect=request;m._last_poll=float('-inf');await m.async_update()
    assert m.racks['10.2.2.3'].dimmers['circuits'][0]['circuit']==100
    assert m._request.await_count==8


def test_system_labels_transcribed_from_real_screenshot():
    body=(F/'system_observed_text.html').read_text()
    assert cem.validate_cem3_identity(body)
    data=cem.parse_cem3_system_html(body)
    assert data['rack_name']=='grada salle A2' and data['rack_number']==2
    assert data['software_version']=='1.7.4.9.0.105'
    assert [data[f'phase_{p}_voltage_v'] for p in 'xyz']==[240,242,235]
    assert data['errors']==['No Data DMX port A']
    assert data['cpu_temperature_c'] is None  # Not displayed on this page.
