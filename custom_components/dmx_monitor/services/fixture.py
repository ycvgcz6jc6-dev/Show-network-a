"""GDTF fixture import, patching and fixed-state control services."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from ..services.common import coordinator_for_call, DOMAIN


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "gdtf_import"):
        return

    async def _import(call):
        c = coordinator_for_call(hass, call)
        result = await hass.async_add_executor_job(c.fixture_control.import_gdtf, str(call.data["filename"]))
        c.publish(**c.fixture_control.snapshot())
        return result

    async def _patch_upsert(call):
        c = coordinator_for_call(hass, call)
        data = dict(call.data)
        await hass.async_add_executor_job(c.fixture_control.upsert_patch, data)
        c.publish(**c.fixture_control.snapshot())
        callback = getattr(c, "fixture_number_refresh_callback", None)
        if callback:
            callback()

    async def _patch_remove(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await hass.async_add_executor_job(c.fixture_control.remove_patch, str(call.data["patch_id"]))
        c.publish(**c.fixture_control.snapshot())

    async def _set_attribute(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        c.fixture_control.set_attribute(str(call.data["patch_id"]), str(call.data["attribute"]), float(call.data["value"]))
        await c.fixture_control.send_now(str(call.data["patch_id"]))
        c.publish(**c.fixture_control.snapshot())

    hass.services.async_register(DOMAIN, "gdtf_import", _import)
    hass.services.async_register(DOMAIN, "fixture_patch_upsert", _patch_upsert)
    hass.services.async_register(DOMAIN, "fixture_patch_remove", _patch_remove)
    hass.services.async_register(DOMAIN, "fixture_set_attribute", _set_attribute)
