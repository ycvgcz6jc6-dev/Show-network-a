"""Persistent Incident Center operator actions."""
from homeassistant.core import HomeAssistant
from .common import coordinator_for_call, DOMAIN
async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN,"incident_acknowledge"): return
    async def acknowledge(call):
        c=coordinator_for_call(hass,call)
        await hass.async_add_executor_job(c.incident_center.acknowledge,str(call.data["incident_id"]),str(call.data.get("operator") or "operator"))
        await c.async_request_refresh()
    hass.services.async_register(DOMAIN,"incident_acknowledge",acknowledge)
