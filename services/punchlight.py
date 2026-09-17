"""Show Network punchlight service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN
from ..punchlight_network import async_scan as async_scan_punchlight_network

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "discover_punchlight"):
        async def _discover_punchlight(call):
            c = coordinator_for_call(hass, call)
            interface_name = str(call.data.get("interface", "0.0.0.0"))
            timeout = max(0.5, min(float(call.data.get("timeout", 2.0)), 10.0))
            devices = await async_scan_punchlight_network(hass, interface_name, timeout)
            c.publish(punchlight_network=devices)
            if c.archive:
                c.archive.record("punchlight", "network_discovery", {"interface": interface_name, "count": len(devices)})
        hass.services.async_register(DOMAIN, "discover_punchlight", _discover_punchlight)
