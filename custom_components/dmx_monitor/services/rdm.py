"""RDM/RDMnet services with explicit security and write arming."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from .common import coordinator_for_call, DOMAIN
from ..rdm_inventory import normalize_uid


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "rdm_refresh"):
        return

    async def _refresh(call):
        c = coordinator_for_call(hass, call)
        for bridge in (getattr(c, "rdm_bridge", None), getattr(c, "rdmnet_bridge", None)):
            if bridge:
                await bridge.async_update()
        c.publish(**c.rdm_inventory.snapshot())

    async def _set(call, pid: str):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        if not bool(getattr(c, "rdm_allow_writes", False)):
            raise PermissionError("RDM writes are not armed in Show Network options")
        transport = str(call.data.get("transport", "RDM/OLA"))
        bridge = c.rdmnet_bridge if transport.lower() == "rdmnet" else c.rdm_bridge
        if bridge is None:
            raise RuntimeError(f"{transport} bridge is not configured")
        uid = normalize_uid(str(call.data["uid"]))
        return await bridge.async_set(
            uid=uid,
            universe=call.data.get("universe"),
            scope=call.data.get("scope"),
            pid=pid,
            value=call.data["value"],
        )

    async def _address(call): return await _set(call, "dmx_start_address")
    async def _personality(call): return await _set(call, "dmx_personality")
    async def _identify(call): return await _set(call, "identify_device")

    async def _link(call):
        c = coordinator_for_call(hass, call)
        uid = normalize_uid(str(call.data["uid"]))
        patch = c.fixture_control.patches.get(str(call.data["patch_id"]))
        if patch is None:
            raise ValueError("Unknown GDTF patch")
        patch.rdm_uid = uid
        await hass.async_add_executor_job(c.fixture_control.save)
        c.publish(**c.fixture_control.snapshot())

    hass.services.async_register(DOMAIN, "rdm_refresh", _refresh)
    hass.services.async_register(DOMAIN, "rdm_set_start_address", _address)
    hass.services.async_register(DOMAIN, "rdm_set_personality", _personality)
    hass.services.async_register(DOMAIN, "rdm_identify", _identify)
    hass.services.async_register(DOMAIN, "rdm_link_fixture", _link)
