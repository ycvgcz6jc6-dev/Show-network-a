"""DMX scene-bank services."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from .common import coordinator_for_call, DOMAIN, guarded


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "dmx_scene_recall"):
        return

    async def _configure(call):
        c = coordinator_for_call(hass, call)
        await hass.async_add_executor_job(c.dmx_scene_bank.configure_output, dict(call.data))
        c.publish(**c.dmx_scene_bank.snapshot())

    async def _save(call):
        c = coordinator_for_call(hass, call)
        await hass.async_add_executor_job(
            c.dmx_scene_bank.upsert_scene,
            str(call.data["scene_id"]),
            str(call.data.get("name") or call.data["scene_id"]),
            list(call.data.get("values") or []),
        )
        c.publish(**c.dmx_scene_bank.snapshot())
        callback = getattr(c, "dmx_scene_refresh_callback", None)
        if callback:
            callback()

    async def _delete(call):
        c = coordinator_for_call(hass, call)
        await hass.async_add_executor_job(c.dmx_scene_bank.delete_scene, str(call.data["scene_id"]))
        c.publish(**c.dmx_scene_bank.snapshot())

    async def _enable(call):
        c = coordinator_for_call(hass, call)
        enabled = bool(call.data["enabled"])
        if enabled:
            c.security.require_unlocked()
        c.dmx_scene_bank.set_enabled(enabled)
        c.publish(**c.dmx_scene_bank.snapshot())

    async def _recall(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await c.dmx_scene_bank.recall(str(call.data["scene_id"]))
        c.publish(**c.dmx_scene_bank.snapshot())

    hass.services.async_register(DOMAIN, "dmx_scene_configure_output", guarded(_configure))
    hass.services.async_register(DOMAIN, "dmx_scene_save", guarded(_save))
    hass.services.async_register(DOMAIN, "dmx_scene_delete", guarded(_delete))
    hass.services.async_register(DOMAIN, "dmx_scene_set_enabled", guarded(_enable))
    hass.services.async_register(DOMAIN, "dmx_scene_recall", guarded(_recall))
