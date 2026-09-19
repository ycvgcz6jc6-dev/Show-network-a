"""Show reference snapshot services."""
from homeassistant.core import HomeAssistant
from .common import coordinator_for_call, DOMAIN
async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN,"show_snapshot_create"): return
    async def create(call):
        c=coordinator_for_call(hass,call); await hass.async_add_executor_job(c.show_snapshots.create,str(call.data.get("name","Show")),dict(c.data)); await c.async_request_refresh()
    async def activate(call):
        c=coordinator_for_call(hass,call); await hass.async_add_executor_job(c.show_snapshots.activate,str(call.data["name"])); await c.async_request_refresh()
    async def delete(call):
        c=coordinator_for_call(hass,call); await hass.async_add_executor_job(c.show_snapshots.delete,str(call.data["name"])); await c.async_request_refresh()
    hass.services.async_register(DOMAIN,"show_snapshot_create",create); hass.services.async_register(DOMAIN,"show_snapshot_activate",activate); hass.services.async_register(DOMAIN,"show_snapshot_delete",delete)
