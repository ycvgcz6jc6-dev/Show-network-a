"""Switch entities for Show Network.

Two active output toggles that already exist as gated coordinator methods
(set_light_sync_enabled / set_osc_output_enabled -- both call
security.require_unlocked() internally before taking effect, see
coordinator.py), plus the already-existing ha_builder_entities.BuilderSwitch
for user-defined toggles -- exactly the same "static + ha_builder dynamic"
shape already used by binary_sensor.py/number.py/sensor.py.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ha_builder_entities import BuilderSwitch


class LightSyncSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Synchronisation DMX → lumières HA"
    _attr_icon = "mdi:lightbulb-multiple"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "show_network_light_sync_enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("light_sync_enabled"))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.set_light_sync_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.set_light_sync_enabled(False)
        self.async_write_ha_state()


class OSCOutputSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Sortie OSC"
    _attr_icon = "mdi:message-fast"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "show_network_osc_output_enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("osc_output_enabled"))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.set_osc_output_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.set_osc_output_enabled(False)
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [LightSyncSwitch(coordinator), OSCOutputSwitch(coordinator)]
    entities.extend(
        BuilderSwitch(coordinator, item)
        for item in coordinator.ha_builder.items.values()
        if item.entity_type == "switch" and item.enabled
    )
    async_add_entities(entities)

    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    coordinator.ha_builder_callbacks["switch"] = lambda item: async_add_entities([BuilderSwitch(coordinator, item)])
