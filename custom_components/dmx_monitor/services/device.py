"""Show Network device service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "set_device_override"):
        async def _set_device_override(call):
            coordinator = coordinator_for_call(hass, call)
            uid = str(call.data["unique_id"])
            if uid not in coordinator.inventory.devices:
                raise ValueError(f"Unknown device: {uid}")
            coordinator.inventory.set_override(
                uid, name=call.data.get("name"), manufacturer=call.data.get("manufacturer"),
                model=call.data.get("model"), location=call.data.get("location"),
                role=call.data.get("role"), hidden=call.data.get("hidden"), monitor_mode=call.data.get("monitor_mode"),
            )
            coordinator.publish(device_inventory=coordinator.inventory.public())

        async def _clear_device_override(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.inventory.clear_override(str(call.data["unique_id"]))
            coordinator.publish(device_inventory=coordinator.inventory.public())

        hass.services.async_register(DOMAIN, "set_device_override", _set_device_override)
        async def _scan_network(call):
            coordinator = coordinator_for_call(hass, call)
            scan = getattr(coordinator, "async_scan_network", None)
            if scan is None:
                raise ValueError("Network discovery is not available")
            await scan()
            coordinator.publish(device_inventory=coordinator.inventory.public(include_hidden=True))

        hass.services.async_register(DOMAIN, "clear_device_override", _clear_device_override)
        hass.services.async_register(DOMAIN, "scan_network", _scan_network)
