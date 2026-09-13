"""Service registry for Show Network.

Handlers are grouped by responsibility so the integration entry point remains
small and protocol/domain changes do not create a single service monolith.
"""
from __future__ import annotations
from homeassistant.core import HomeAssistant
from . import device, rules, projector, dmx, control, security, osc, builder, notification, chaos, punchlight, archive

async def async_register_services(hass: HomeAssistant) -> None:
    for module in (device, rules, projector, dmx, control, security, osc, builder, notification, chaos, punchlight, archive):
        await module.async_register(hass)
