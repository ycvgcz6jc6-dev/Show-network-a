"""Show Network projector service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN


def _target(coordinator, host: str, fallback_port: int) -> tuple[str, dict]:
    rec = coordinator.projector_monitor.get_record(host) if getattr(coordinator, "projector_monitor", None) else None
    cfg = coordinator.projector_monitor.config_for(host) if getattr(coordinator, "projector_monitor", None) else {}
    if rec is not None:
        cfg.setdefault("port", rec.port)
        profile = rec.profile
    else:
        cfg.setdefault("port", fallback_port)
        profile = "pjlink"
    return profile, cfg


async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "projector_power"):
        async def _execute(call, command: str, value=None):
            coordinator = coordinator_for_call(hass, call)
            ctrl = coordinator.projector_controller
            if not ctrl.control_enabled:
                raise PermissionError("projector control is disabled")
            coordinator.security.require_unlocked()
            host = str(call.data["host"])
            fallback_port = int(call.data.get("port", 4352))
            profile, cfg = _target(coordinator, host, fallback_port)
            result = await hass.async_add_executor_job(
                ctrl.send, host, profile=profile, config=cfg, name=command, value=value
            )
            if coordinator.archive:
                coordinator.archive.record("projector", "projector_command", {
                    "host": host, "profile": profile, "command": command,
                    "result": str(result)[:512],
                })
            return result

        async def _projector_power(call):
            command = "power_on" if bool(call.data["on"]) else "standby"
            await _execute(call, command)

        async def _projector_input(call):
            await _execute(call, "input", str(call.data["input"]))

        async def _projector_mute(call):
            command = "av_mute_on" if bool(call.data["mute"]) else "av_mute_off"
            await _execute(call, command)

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
