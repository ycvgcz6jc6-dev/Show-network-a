"""Show Network security service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "set_security_password"):
        async def _set_security_password(call):
            c = coordinator_for_call(hass, call)
            if c.security.state.configured:
                current = str(call.data.get("current_password", ""))
                if not await hass.async_add_executor_job(c.security.verify, current):
                    raise PermissionError("Current Show Network password is invalid")
            await hass.async_add_executor_job(c.security.set_password, str(call.data["password"]))
            c.publish(security=c.security.snapshot())
        async def _unlock_security(call):
            c = coordinator_for_call(hass, call)
            await hass.async_add_executor_job(c.security.unlock, str(call.data["password"]))
            c.publish(security=c.security.snapshot())
        async def _lock_security(call):
            c = coordinator_for_call(hass, call)
            c.security.lock()
            # Stop any in-progress power sequence at its current frame. The
            # maintained frame is not zeroed, avoiding an unsafe automatic cut.
            await c.power_manager.cancel_transitions("Show Network security locked")
            c.set_osc_output_enabled(False, require_security=False)
            c.set_light_sync_enabled(False, require_security=False)
            c.projector_controller.set_control_enabled(False)
            c.midi_output.set_enabled(False)
            c.show_control.enabled = False
            c.publish(security=c.security.snapshot(), projector_control_enabled=False, midi_output=c.midi_output.snapshot(), **c.show_control.snapshot())
        hass.services.async_register(DOMAIN, "set_security_password", guarded(_set_security_password))
        hass.services.async_register(DOMAIN, "unlock_security", guarded(_unlock_security))
        hass.services.async_register(DOMAIN, "lock_security", guarded(_lock_security))
