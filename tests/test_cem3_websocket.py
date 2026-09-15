"""HA websocket handler contract tested using a minimal HA API adapter."""
import importlib
import sys
from types import ModuleType,SimpleNamespace
from unittest.mock import Mock
import pytest


@pytest.mark.asyncio
async def test_websocket_uses_cache_aggregates_entries_and_follows_unload(monkeypatch):
    api=ModuleType('homeassistant.components.websocket_api')
    api.websocket_command=lambda schema:lambda f:f
    api.async_response=lambda f:f
    api.async_register_command=Mock()
    components=ModuleType('homeassistant.components');components.websocket_api=api
    for key,value in [('homeassistant',ModuleType('homeassistant')),('homeassistant.components',components),('homeassistant.components.websocket_api',api)]:monkeypatch.setitem(sys.modules,key,value)
    sys.modules.pop('custom_components.dmx_monitor.cem3_websocket',None)
    ws=importlib.import_module('custom_components.dmx_monitor.cem3_websocket')
    def monitor(host):return SimpleNamespace(snapshot=lambda:{'racks':[{'host':host,'online':True,'fresh':True,'dimmers':{'circuits':[{'udn':i} for i in range(72)]}}], 'source_ips':['10.1.0.1'],'discovery_status':'ready'})
    hass=SimpleNamespace(data={'dmx_monitor':{key:{'coordinator':SimpleNamespace(etc_cem3_monitor=monitor(key))} for key in ['a','b']}})
    connection=SimpleNamespace(send_result=Mock())
    ws.async_register(hass);ws.async_register(hass);api.async_register_command.assert_called_once()
    await ws.websocket_cem3(hass,connection,{'id':1})
    result=connection.send_result.call_args.args[1]
    assert result['online']==2 and len(result['racks'][1]['dimmers']['circuits'])==72
    assert result['racks'][0]['entry_id']=='a'
    hass.data['dmx_monitor'].clear()
    await ws.websocket_cem3(hass,connection,{'id':2})
    assert connection.send_result.call_args.args[1]['racks']==[]
