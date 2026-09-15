import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import socket
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from custom_components.dmx_monitor.core.state_store import RuntimeStateStore
from custom_components.dmx_monitor.lighting_receiver import UniverseTracker,DmxNetworkReceiver
from custom_components.dmx_monitor.rate_limiter import RateLimiter
from custom_components.dmx_monitor.resource_registry import ResourceRegistry,RuntimeResource,ProtocolDriver
import custom_components.dmx_monitor as integration


def test_concurrent_state_store_snapshots_are_bounded_and_isolated():
    store=RuntimeStateStore(max_keys=64,history_limit=20)
    def worker(n):
        for i in range(300):
            store.update(**{str(n):{'index':i}})
            snap=store.snapshot();history=store.history()
            assert len(snap)<=64 and len(history)<=20
            snap[str(n)]['index']=-100
            assert store.get(str(n))['index']>=0
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(worker,range(8)))
    data={'nested':[1]};store.update(test=data);data['nested'].clear()
    assert store.get('test')['nested']==[1]
    result=store.get('test');result['nested'].clear()
    assert store.get('test')['nested']==[1]
    store.update(**{f'key{i}':i for i in range(100)})
    assert len(store.snapshot())==64


def test_concurrent_dmx_tracker_with_eviction_and_detached_results():
    tracker=UniverseTracker(max_items=64)
    def worker(n):
        for i in range(200):
            row=tracker.observe('SACN',i,n,bytes([i%256])*512,sequence=i%256)
            row.universe=-1
            assert all(r.universe>=0 for r in tracker.all())
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(worker,range(8)))
    assert len(tracker.all())<=64
    snap=tracker.all();snap[0].universe=-1
    assert all(r.universe>=0 for r in tracker.all())


@pytest.mark.asyncio
async def test_dmx_publication_rate_coalesces_burst_to_five_hz():
    limiter=RateLimiter(.2);seen=[]
    async def send(value):seen.append((asyncio.get_running_loop().time(),value))
    for i in range(80):limiter.push_nowait(i,send);await asyncio.sleep(.005)
    await asyncio.sleep(.25);await limiter.async_stop()
    assert 2<=len(seen)<=4 and seen[-1][1]==79
    assert all(b[0]-a[0]>=.19 for a,b in zip(seen,seen[1:]))
    assert limiter._task is None


@pytest.mark.asyncio
@pytest.mark.parametrize('protocol',['ARTNET','SACN'])
async def test_udp_stop_restart_releases_socket(protocol):
    # Ephemeral localhost ports avoid interfering with running show software.
    receiver=DmxNetworkReceiver('127.0.0.1',lambda *a:None,artnet_enabled=False,sacn_enabled=False)
    for _ in range(3):
        sock=await receiver._open_socket(protocol,0,None)
        port=sock.getsockname()[1]
        await receiver.stop()
        assert sock.fileno()==-1
        probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:probe.bind(('127.0.0.1',port))
        finally:probe.close()


@pytest.mark.asyncio
async def test_ha_unload_lifecycle_with_real_resource_registry():
    resource=SimpleNamespace(stop=AsyncMock())
    registry=ResourceRegistry();registry.add(RuntimeResource(ProtocolDriver('test','LIGHT'),'test',resource))
    coordinator=SimpleNamespace(watchdogs=SimpleNamespace(async_stop=AsyncMock()),async_stop=AsyncMock())
    archive=SimpleNamespace(record=lambda *a,**kw:None,async_stop=AsyncMock())
    hass=SimpleNamespace(data={'dmx_monitor':{'entry':{'resource_registry':registry,'coordinator':coordinator,'archive':archive}}},config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True)))
    assert await integration.async_unload_entry(hass,SimpleNamespace(entry_id='entry'))
    resource.stop.assert_awaited_once();coordinator.async_stop.assert_awaited_once();archive.async_stop.assert_awaited_once()
    assert not registry.snapshot() and not hass.data['dmx_monitor']


@pytest.mark.asyncio
async def test_ha_failed_platform_unload_preserves_runtime():
    registry=ResourceRegistry();resource=SimpleNamespace(stop=AsyncMock())
    registry.add(RuntimeResource(ProtocolDriver('test','LIGHT'),'test',resource))
    hass=SimpleNamespace(data={'dmx_monitor':{'entry':{'resource_registry':registry}}},config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=False)))
    assert not await integration.async_unload_entry(hass,SimpleNamespace(entry_id='entry'))
    resource.stop.assert_not_awaited();assert 'entry' in hass.data['dmx_monitor']
