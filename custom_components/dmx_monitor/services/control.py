"""Show Network control service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded
from ..osc_mapping import Mapping

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "create_control_mapping"):
        async def _create_control_mapping(call):
            coordinator = coordinator_for_call(hass, call)
            from ..osc_mapping import Mapping
            data=call.data
            m=Mapping(
                mapping_id=str(data["mapping_id"]), address=str(data["address"]),
                destination=str(data.get("destination", "number.set_value")), target=str(data["target"]),
                attribute=data.get("attribute"),
                in_min=float(data.get("in_min", 0.0)), in_max=float(data.get("in_max", 1.0)),
                out_min=float(data.get("out_min", 0.0)), out_max=float(data.get("out_max", 1.0)),
                invert=bool(data.get("invert", False)),
                min_interval_ms=int(data.get("min_interval_ms", 200)), deadband=float(data.get("deadband", 0)),
            )
            if "." not in m.destination:
                raise ValueError("destination doit être au format domaine.service")
            domain, service = m.destination.split(".", 1)
            if not hass.services.has_service(domain, service):
                raise ValueError(f"Service Home Assistant indisponible: {m.destination}")
            coordinator.control_mapping_engine.add(m)
            coordinator.control_mapping_store.save([__import__("dataclasses").asdict(x) for x in coordinator.control_mapping_engine.mappings.values()])
            coordinator.publish(control_mappings=list(coordinator.control_mapping_engine.mappings))
        async def _remove_control_mapping(call):
            coordinator = coordinator_for_call(hass, call)
            from ..control_mapping import ControlMappingStore
            coordinator.control_mapping_engine.remove(str(call.data["mapping_id"]))
            coordinator.control_mapping_store.save([__import__("dataclasses").asdict(x) for x in coordinator.control_mapping_engine.mappings.values()])
            coordinator.publish(control_mappings=list(coordinator.control_mapping_engine.mappings))
        hass.services.async_register(DOMAIN, "create_control_mapping", guarded(_create_control_mapping))
        hass.services.async_register(DOMAIN, "remove_control_mapping", guarded(_remove_control_mapping))
