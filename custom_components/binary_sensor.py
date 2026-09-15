from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .ha_builder_entities import BuilderBinarySensor
from .projector_platform import binary_entities as projector_binary_entities

class PunchLightRecording(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "PunchLight — Enregistrement"
    _attr_icon = "mdi:record-rec"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "punchlight_recording"
    @property
    def is_on(self):
        return bool(self.coordinator.data.get("punchlight", {}).get("recording"))
    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data.get("punchlight", {}))


class TallyIPOn(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Tally IP — ON"
    _attr_icon = "mdi:tally-mark-1"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "tally_ip_on"

    @property
    def is_on(self):
        return bool(self.coordinator.data.get("tally_ip", {}).get("on"))

    @property
    def available(self):
        state = self.coordinator.data.get("tally_ip", {})
        return bool(state.get("enabled") and state.get("listening"))

    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data.get("tally_ip", {}))

class PunchLightReady(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "PunchLight — Ready"
    _attr_icon = "mdi:record-circle-outline"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "punchlight_ready"
    @property
    def is_on(self):
        return bool(self.coordinator.data.get("punchlight", {}).get("ready"))
    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data.get("punchlight", {}))

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    # Protocol labels may arrive with different casing (sACN/SACN). Normalize
    # before entity creation so HA never receives duplicate unique IDs.
    canonical = {}
    for x in coordinator.dmx_tracker.all():
        canonical[(str(x.protocol).strip().lower(), int(x.universe))] = (x.protocol, int(x.universe))
    seen = set(canonical)
    entities = [UniverseActive(coordinator, *canonical[key]) for key in sorted(seen, key=str)]
    entities.extend([PunchLightRecording(coordinator), PunchLightReady(coordinator)])
    if coordinator.data.get("tally_ip", {}).get("enabled"):
        entities.append(TallyIPOn(coordinator))
    entities.extend(projector_binary_entities(coordinator))
    entities.extend(BuilderBinarySensor(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "binary_sensor" and item.enabled)
    async_add_entities(entities)
    coordinator._dmx_universe_entity_keys = set(seen)
    def _add_universe(protocol, universe):
        key = (str(protocol).strip().lower(), int(universe))
        if key in coordinator._dmx_universe_entity_keys:
            return
        coordinator._dmx_universe_entity_keys.add(key)
        async_add_entities([UniverseActive(coordinator, protocol, universe)])
    coordinator.dmx_universe_entity_callback = _add_universe
    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    coordinator.ha_builder_callbacks["binary_sensor"] = lambda item: async_add_entities([BuilderBinarySensor(coordinator, item)])
    coordinator.ha_builder_remove_callbacks = getattr(coordinator, "ha_builder_remove_callbacks", {})

class UniverseActive(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "DMX universe active"

    def __init__(self, coordinator, protocol, universe):
        super().__init__(coordinator)
        self._key = (protocol, universe)
        safe = f"{str(protocol).strip().lower()}_{int(universe)}".replace(" ", "_").replace(":", "_")
        self._attr_unique_id = f"dmx_universe_{safe}_active"
        self._attr_extra_state_attributes = {}

    def _items(self):
        return [x for x in self.coordinator.dmx_tracker.all() if (x.protocol, x.universe) == self._key]

    @property
    def is_on(self):
        return any(x.active_channels > 0 for x in self._items())

    @property
    def extra_state_attributes(self):
        items = self._items()
        return {
            "protocol": self._key[0],
            "universe": self._key[1],
            "sources": [x.source for x in items],
            "active_channels": max((x.active_channels for x in items), default=0),
            "packet_rate": max((x.packet_rate for x in items), default=0),
        }
