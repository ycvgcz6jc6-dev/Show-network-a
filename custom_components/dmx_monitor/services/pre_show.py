"""Optional Pre-Show profile services. Diagnostic only, never a gate."""
from homeassistant.core import HomeAssistant
from functools import partial
from .common import coordinator_for_call, DOMAIN, guarded
async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN,"pre_show_profile_set"): return
    async def set_profile(call):
        c=coordinator_for_call(hass,call); d=dict(call.data)
        for k in ("expected_dmx_universes","expected_devices"):
            v=d.get(k)
            if isinstance(v,str): d[k]=[x.strip() for x in v.split(",") if x.strip()]
        await hass.async_add_executor_job(partial(c.pre_show.configure,**d)); await c.async_request_refresh()
    async def disable(call):
        c=coordinator_for_call(hass,call); await hass.async_add_executor_job(c.pre_show.disable); await c.async_request_refresh()
    hass.services.async_register(DOMAIN, "pre_show_profile_set", guarded(set_profile))
    hass.services.async_register(DOMAIN, "pre_show_profile_disable", guarded(disable))
