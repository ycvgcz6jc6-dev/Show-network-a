"""Show Network projector service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN
from ..projector import ProjectorController

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "projector_power"):
        async def _projector_power(call):
            coordinator = coordinator_for_call(hass, call)
            ctrl = coordinator.projector_controller
            if not ctrl.control_enabled:
                raise PermissionError("projector control is disabled")
            coordinator.security.require_unlocked()
            host = str(call.data["host"])
            port = int(call.data.get("port", 4352))
            command = "power_on" if bool(call.data["on"]) else "standby"
            await hass.async_add_executor_job(ProjectorController.send_pjlink, ctrl, host, port, command, None)

        async def _projector_input(call):
            coordinator = coordinator_for_call(hass, call)
            ctrl = coordinator.projector_controller
            if not ctrl.control_enabled:
                raise PermissionError("projector control is disabled")
            coordinator.security.require_unlocked()
            await hass.async_add_executor_job(ProjectorController.send_pjlink, ctrl, str(call.data["host"]), int(call.data.get("port", 4352)), "input", str(call.data["input"]))

        async def _projector_mute(call):
            coordinator = coordinator_for_call(hass, call)
            ctrl = coordinator.projector_controller
            if not ctrl.control_enabled:
                raise PermissionError("projector control is disabled")
            coordinator.security.require_unlocked()
            command = "av_mute_on" if bool(call.data["mute"]) else "av_mute_off"
            await hass.async_add_executor_job(ProjectorController.send_pjlink, ctrl, str(call.data["host"]), int(call.data.get("port", 4352)), command, None)

        async def _projector_control(call):
            coordinator = coordinator_for_call(hass, call)
            if bool(call.data.get("enabled", False)):
                coordinator.security.require_unlocked()
            coordinator.projector_controller.set_control_enabled(bool(call.data.get("enabled", False)))
            coordinator.publish(projector_control_enabled=coordinator.projector_controller.control_enabled)
            if coordinator.archive:
                coordinator.archive.record("system", "projector_control_gate_changed", {"enabled": coordinator.projector_controller.control_enabled})

        hass.services.async_register(DOMAIN, "projector_power", _projector_power)
        hass.services.async_register(DOMAIN, "projector_input", _projector_input)
        hass.services.async_register(DOMAIN, "projector_mute", _projector_mute)
        hass.services.async_register(DOMAIN, "set_projector_control_enabled", _projector_control)
