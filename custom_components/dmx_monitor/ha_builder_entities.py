from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

class BuilderBase(CoordinatorEntity):
    def __init__(self, coordinator, item):
        super().__init__(coordinator)
        self.item_id = item.item_id
        self._attr_unique_id = f"ha_builder_{item.item_id}"
        self._attr_name = item.name
        self._attr_has_entity_name = False
        self._attr_icon = item.icon
        self._attr_device_class = item.device_class
        self._attr_extra_state_attributes = {"show_network_builder": True, "area": item.area} if item.area else {"show_network_builder": True}

class BuilderSwitch(BuilderBase, SwitchEntity):
    def __init__(self, coordinator, item): super().__init__(coordinator, item)
    @property
    def is_on(self): return bool(self.coordinator.ha_builder.items[self.item_id].state if self.item_id in self.coordinator.ha_builder.items else False)
    async def async_turn_on(self, **kwargs):
        self.coordinator.ha_builder.set_state(self.item_id, True); self.async_write_ha_state()
    async def async_turn_off(self, **kwargs):
        self.coordinator.ha_builder.set_state(self.item_id, False); self.async_write_ha_state()

class BuilderBinarySensor(BuilderBase, BinarySensorEntity):
    @property
    def is_on(self):
        item = self.coordinator.ha_builder.items.get(self.item_id)
        return bool(item.state) if item else False

class BuilderSensor(BuilderBase, SensorEntity):
    @property
    def native_value(self):
        item = self.coordinator.ha_builder.items.get(self.item_id)
        return item.state if item else None
    @property
    def native_unit_of_measurement(self):
        item = self.coordinator.ha_builder.items.get(self.item_id)
        return item.unit if item else None


class BuilderButton(BuilderBase, ButtonEntity):
    async def async_press(self) -> None:
        item = self.coordinator.ha_builder.items.get(self.item_id)
        if item:
            self.coordinator.ha_builder.set_state(self.item_id, True)
            self.coordinator.ha_builder.set_state(self.item_id, False)
            self.async_write_ha_state()


class BuilderNumber(BuilderBase, NumberEntity):
    def __init__(self, coordinator, item):
        super().__init__(coordinator, item)
        self._attr_native_min_value = float(item.min_value if item.min_value is not None else 0)
        self._attr_native_max_value = float(item.max_value if item.max_value is not None else 100)
        self._attr_native_step = float(item.step if item.step is not None else 1)
        self._attr_native_unit_of_measurement = item.unit

    @property
    def native_value(self):
        item = self.coordinator.ha_builder.items.get(self.item_id)
        try:
            return float(item.state) if item and item.state is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.ha_builder.set_state(self.item_id, float(value))
        self.async_write_ha_state()
