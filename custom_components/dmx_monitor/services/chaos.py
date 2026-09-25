"""Show Network chaos service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "chaos_signal_loss"):
        async def _chaos_signal_loss(call):
            c = coordinator_for_call(hass, call)
            if not getattr(c, "chaos_enabled", False): raise ValueError("Diagnostics / chaos tests are disabled")
            await c.simulate_signal_loss(call.data.get("watchdog"))
        async def _chaos_signal_restore(call):
            c = coordinator_for_call(hass, call)
            if not getattr(c, "chaos_enabled", False): raise ValueError("Diagnostics / chaos tests are disabled")
            await c.simulate_signal_restore(call.data.get("watchdog"))
        async def _chaos_ptp_drift(call):
            c = coordinator_for_call(hass, call)
            if not getattr(c, "chaos_enabled", False): raise ValueError("Diagnostics / chaos tests are disabled")
            c.simulate_ptp_drift(float(call.data.get("offset_ms", 1.0)))
        async def _chaos_clear(call):
            c = coordinator_for_call(hass, call)
            if not getattr(c, "chaos_enabled", False): raise ValueError("Diagnostics / chaos tests are disabled")
            c.clear_chaos()
        hass.services.async_register(DOMAIN, "chaos_signal_loss", guarded(_chaos_signal_loss))
        hass.services.async_register(DOMAIN, "chaos_signal_restore", guarded(_chaos_signal_restore))
        hass.services.async_register(DOMAIN, "chaos_ptp_drift", guarded(_chaos_ptp_drift))
        hass.services.async_register(DOMAIN, "chaos_clear", guarded(_chaos_clear))
