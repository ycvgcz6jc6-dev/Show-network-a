"""QLC+ Virtual Console control services (gated -- see qlcplus_bridge.py)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from .common import coordinator_for_call, DOMAIN, guarded


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "qlcplus_set_widget_value"):
        return

    def _bridge(coordinator):
        bridge = getattr(coordinator, "qlcplus_bridge", None)
        if bridge is None:
            raise RuntimeError("QLC+ is not configured (see Show Network options)")
        return bridge

    async def _set_widget_value(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await _bridge(c).set_widget_value(str(call.data["widget_id"]), int(call.data["value"]))

    async def _cue_list_control(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await _bridge(c).cue_list_control(
            str(call.data["widget_id"]), str(call.data["operation"]), call.data.get("step"),
        )

    async def _frame_control(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await _bridge(c).frame_control(str(call.data["widget_id"]), str(call.data["operation"]))

    async def _set_function_status(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        await _bridge(c).set_function_status(str(call.data["function_id"]), bool(call.data["running"]))

    async def _refresh(call):
        c = coordinator_for_call(hass, call)
        await _bridge(c).async_update()
        c.publish(**_bridge(c).snapshot())

    hass.services.async_register(DOMAIN, "qlcplus_set_widget_value", guarded(_set_widget_value))
    hass.services.async_register(DOMAIN, "qlcplus_cue_list_control", guarded(_cue_list_control))
    hass.services.async_register(DOMAIN, "qlcplus_frame_control", guarded(_frame_control))
    hass.services.async_register(DOMAIN, "qlcplus_set_function_status", guarded(_set_function_status))
    hass.services.async_register(DOMAIN, "qlcplus_refresh", guarded(_refresh))
