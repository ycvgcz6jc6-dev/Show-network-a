"""Show Network dmx service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN
from ..rules import parse_channel_selection
from ..dmx_ha_mapping import DmxHAMapping
from ..dmx_ha_zones import DmxHAZone

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "create_dmx_ha_mapping"):
        async def _create_dmx_ha_mapping(call):
            coordinator = coordinator_for_call(hass, call)
            from .dmx_ha_mapping import DmxHAMapping
            from ..dmx_ha_mapping_storage import DmxHAMappingStore
            import dataclasses
            data = call.data
            channels = tuple(parse_channel_selection(str(data["channels"])))
            mapping = DmxHAMapping(
                mapping_id=str(data["mapping_id"]), universe=int(data["universe"]), channels=channels,
                entity_id=data.get("entity_id") or None, domain=str(data.get("domain", "light")),
                service=str(data.get("service", "turn_on")), mode=str(data.get("mode", "dimmer")),
                source=data.get("source") or None, min_interval_ms=int(data.get("min_interval_ms", 100)),
                deadband=float(data.get("deadband", 0)), invert=bool(data.get("invert", False)),
                enabled=bool(data.get("enabled", True)), data=dict(data.get("data") or {}),
            )
            coordinator.dmx_ha_mapping_engine.add(mapping)
            coordinator.save_dmx_ha_mappings()
            coordinator.publish(dmx_ha_mappings=coordinator.dmx_ha_mapping_engine.snapshot())

        async def _remove_dmx_ha_mapping(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.dmx_ha_mapping_engine.remove(str(call.data["mapping_id"]))
            coordinator.save_dmx_ha_mappings()
            coordinator.publish(dmx_ha_mappings=coordinator.dmx_ha_mapping_engine.snapshot())

        async def _create_dmx_ha_zone(call):
            coordinator = coordinator_for_call(hass, call)
            from .dmx_ha_zones import DmxHAZone
            data = call.data
            zone = DmxHAZone(
                zone_id=str(data["zone_id"]),
                name=str(data.get("name", data["zone_id"])),
                universe=int(data["universe"]),
                entity_ids=tuple(str(x) for x in data.get("entity_ids", [])),
                mode=str(data.get("mode", "dimmer")),
                channels=tuple(parse_channel_selection(str(data.get("channels", "1")))),
                source=data.get("source") or None,
                enabled=bool(data.get("enabled", True)),
                rdm_enabled=bool(data.get("rdm_enabled", False)),
                fixture_type=str(data.get("fixture_type", "")),
                fixture_types={str(k): str(v) for k, v in dict(data.get("fixture_types") or {}).items()},
                hue_model_id=str(data.get("hue_model_id", "")),
                min_interval_ms=int(data.get("min_interval_ms", 100)),
                deadband=float(data.get("deadband", 0)),
                invert=bool(data.get("invert", False)),
                dimmer_curve=str(data.get("dimmer_curve", "linear")),
            )
            coordinator.dmx_ha_zone_engine.add(zone)
            coordinator.save_dmx_ha_zones()
            coordinator.publish(dmx_ha_zones=coordinator.dmx_ha_zone_engine.snapshot(), dmx_ha_rdm=coordinator.dmx_ha_zone_engine.rdm_snapshot())

        async def _remove_dmx_ha_zone(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.dmx_ha_zone_engine.remove(str(call.data["zone_id"]))
            coordinator.save_dmx_ha_zones()
            coordinator.publish(dmx_ha_zones=coordinator.dmx_ha_zone_engine.snapshot(), dmx_ha_rdm=coordinator.dmx_ha_zone_engine.rdm_snapshot())

        async def _set_dmx_ha_zone_enabled(call):
            coordinator = coordinator_for_call(hass, call)
            zone = coordinator.dmx_ha_zone_engine.zones.get(str(call.data["zone_id"]))
            if not zone:
                raise ValueError("Zone inconnue")
            zone.enabled = bool(call.data["enabled"])
            coordinator.save_dmx_ha_zones()
            coordinator.publish(dmx_ha_zones=coordinator.dmx_ha_zone_engine.snapshot())

        async def _set_dmx_ha_zone_rdm_enabled(call):
            coordinator = coordinator_for_call(hass, call)
            zone = coordinator.dmx_ha_zone_engine.zones.get(str(call.data["zone_id"]))
            if not zone:
                raise ValueError("Zone inconnue")
            zone.rdm_enabled = bool(call.data["enabled"])
            coordinator.save_dmx_ha_zones()
            coordinator.publish(dmx_ha_zones=coordinator.dmx_ha_zone_engine.snapshot())

        async def _observe_dmx_ha_rdm(call):
            coordinator = coordinator_for_call(hass, call)
            accepted = coordinator.dmx_ha_zone_engine.observe_rdm(
                str(call.data["zone_id"]), str(call.data["uid"]),
                call.data.get("manufacturer"), call.data.get("model"), call.data.get("fixture_type"),
            )
            if not accepted:
                raise ValueError("Zone inconnue ou écoute RDM désactivée")
            coordinator.publish(dmx_ha_rdm=coordinator.dmx_ha_zone_engine.rdm_snapshot())

        async def _set_dmx_ha_mapping_highlight(call):
            coordinator = coordinator_for_call(hass, call)
            await coordinator.async_set_dmx_ha_mapping_highlight(str(call.data["mapping_id"]), bool(call.data["enabled"]))

        hass.services.async_register(DOMAIN, "create_dmx_ha_mapping", _create_dmx_ha_mapping)
        hass.services.async_register(DOMAIN, "remove_dmx_ha_mapping", _remove_dmx_ha_mapping)
        hass.services.async_register(DOMAIN, "set_dmx_ha_mapping_highlight", _set_dmx_ha_mapping_highlight)
        hass.services.async_register(DOMAIN, "create_dmx_ha_zone", _create_dmx_ha_zone)
        hass.services.async_register(DOMAIN, "remove_dmx_ha_zone", _remove_dmx_ha_zone)
        hass.services.async_register(DOMAIN, "set_dmx_ha_zone_enabled", _set_dmx_ha_zone_enabled)
        hass.services.async_register(DOMAIN, "set_dmx_ha_zone_rdm_enabled", _set_dmx_ha_zone_rdm_enabled)
        hass.services.async_register(DOMAIN, "observe_dmx_ha_rdm", _observe_dmx_ha_rdm)
