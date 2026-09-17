"""Power Manager and receive-only DMX Circuit Monitor services."""
from __future__ import annotations
from homeassistant.core import HomeAssistant
from ..services.common import coordinator_for_call, DOMAIN

async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, 'power_manager_upsert_button'):
        return

    async def _power_upsert(call):
        c=coordinator_for_call(hass,call)
        data=dict(call.data); channels=data.get('channels',[]); output=data.get('output',{})
        if isinstance(channels,str):
            import json; channels=json.loads(channels)
        if isinstance(output,str):
            import json; output=json.loads(output)
        data['channels']=channels; data['output']=output
        await hass.async_add_executor_job(c.power_manager.upsert_from_dict,data)
        c.publish(**c.power_manager.snapshot())

    async def _power_remove(call):
        c=coordinator_for_call(hass,call)
        await hass.async_add_executor_job(c.power_manager.remove,str(call.data['button_id']))
        c.publish(**c.power_manager.snapshot())

    async def _power_run(call):
        c=coordinator_for_call(hass,call); c.security.require_unlocked()
        await c.power_manager.run(
            str(call.data['button_id']), bool(call.data.get('on',True)),
            guard=c.security.require_unlocked,
        )
        if c.archive:c.archive.record('power_manager','sequence',{'button_id':str(call.data['button_id']),'on':bool(call.data.get('on',True))})
        c.publish(**c.power_manager.snapshot())

    async def _circuit_upsert(call):
        c=coordinator_for_call(hass,call); data=dict(call.data); circuits=data.get('circuits',[])
        if isinstance(circuits,str):
            import json; circuits=json.loads(circuits)
        data['circuits']=circuits
        await hass.async_add_executor_job(c.dmx_circuit_monitor.upsert,data)
        c.publish(**c.dmx_circuit_monitor.snapshot())

    async def _circuit_remove(call):
        c=coordinator_for_call(hass,call)
        await hass.async_add_executor_job(c.dmx_circuit_monitor.remove,str(call.data['group_id']))
        c.publish(**c.dmx_circuit_monitor.snapshot())

    hass.services.async_register(DOMAIN,'power_manager_upsert_button',_power_upsert)
    hass.services.async_register(DOMAIN,'power_manager_remove_button',_power_remove)
    hass.services.async_register(DOMAIN,'power_manager_run',_power_run)
    hass.services.async_register(DOMAIN,'dmx_circuit_monitor_upsert',_circuit_upsert)
    hass.services.async_register(DOMAIN,'dmx_circuit_monitor_remove',_circuit_remove)
