"""Show Network device service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded

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

        async def _register_manual_device(call):
            coordinator = coordinator_for_call(hass, call)
            import ipaddress
            host = str(call.data["ip"]).strip()
            try:
                ip = str(ipaddress.ip_address(host))
            except ValueError as err:
                raise ValueError(f"Invalid IP address: {host}") from err
            interface = str(call.data.get("interface") or "").strip() or None
            uid = f"manual-ip:{ip}:{interface or 'any'}"
            device = coordinator.inventory.upsert(
                unique_id=uid, ip=ip, interface=interface,
                category="manual_target", protocols={"IP"}, sources={"operator"},
                confidence="operator", confidence_score=1.0,
                evidence=[{"field":"ip","value":ip,"source":"operator_manual_target","confidence":1.0}],
            )
            coordinator.inventory.set_override(
                device.unique_id,
                name=str(call.data.get("name") or "").strip() or None,
                role=str(call.data.get("role") or "").strip() or None,
                monitor_mode=str(call.data.get("monitor_mode") or "monitor"),
            )
            coordinator.publish(device_inventory=coordinator.inventory.public())

        async def _clear_device_override(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.inventory.clear_override(str(call.data["unique_id"]))
            coordinator.publish(device_inventory=coordinator.inventory.public())

        hass.services.async_register(DOMAIN, "set_device_override", guarded(_set_device_override))
        hass.services.async_register(DOMAIN, "register_manual_device", guarded(_register_manual_device))
        async def _scan_network(call):
            coordinator = coordinator_for_call(hass, call)
            scan = getattr(coordinator, "async_scan_network", None)
            if scan is None:
                raise ValueError("Network discovery is not available")
            await scan()
            coordinator.publish(device_inventory=coordinator.inventory.public(include_hidden=True))

        hass.services.async_register(DOMAIN, "clear_device_override", guarded(_clear_device_override))
        hass.services.async_register(DOMAIN, "scan_network", guarded(_scan_network))

        async def _manual_register_amplifier(call):
            coordinator = coordinator_for_call(hass, call)
            host = str(call.data["host"]).strip()
            if not host:
                raise ValueError("host is required")
            coordinator.audio_amplifiers.observe(
                key=f"manual:{host}",
                manufacturer=str(call.data.get("manufacturer") or "").strip() or "Non précisé",
                host=host,
                model=str(call.data.get("model") or "").strip() or None,
                protocol="manual",
                evidence="Enregistré manuellement par l'opérateur (adresse IP connue)",
                device_name=str(call.data.get("name") or "").strip() or None,
            )
            coordinator.publish(**coordinator.audio_amplifiers.snapshot())

        async def _manual_remove_amplifier(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.audio_amplifiers.remove(f"manual:{str(call.data['host']).strip()}")
            coordinator.publish(**coordinator.audio_amplifiers.snapshot())

        hass.services.async_register(DOMAIN, "manual_register_amplifier", guarded(_manual_register_amplifier))
        hass.services.async_register(DOMAIN, "manual_remove_amplifier", guarded(_manual_remove_amplifier))
