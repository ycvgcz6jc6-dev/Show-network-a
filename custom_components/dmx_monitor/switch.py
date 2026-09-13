from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .ha_builder_entities import BuilderSwitch, BuilderButton
class OSCOutputSafetySwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "OSC output safety gate"
    _attr_has_entity_name = True
    _attr_icon = "mdi:access-point-network"
    def __init__(self, c):
        super().__init__(c); self._attr_unique_id = "osc_output_safety_gate"
    @property
    def is_on(self): return bool(self.coordinator.osc_output.enabled)
    async def async_turn_on(self, **kwargs): self.coordinator.set_osc_output_enabled(True)
    async def async_turn_off(self, **kwargs): self.coordinator.set_osc_output_enabled(False)

class EnttecListenSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "ENTTEC DMX input listen"
    _attr_has_entity_name = True
    _attr_icon = "mdi:usb-port"
    def __init__(self, c):
        super().__init__(c)
        self._attr_unique_id = "enttec_dmx_input_listen"
    @property
    def is_on(self):
        return bool(getattr(self.coordinator, "enttec_listen_enabled", False))
    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_enttec_listen_enabled(True)
        self.async_write_ha_state()
    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_enttec_listen_enabled(False)
        self.async_write_ha_state()

class ProjectorControlSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name='Projector control safety lock'
    _attr_has_entity_name=True
    def __init__(self,c):
        super().__init__(c); self._attr_unique_id='projector_control_safety_lock'
    @property
    def is_on(self): return bool(self.coordinator.projector_controller.control_enabled)
    async def async_turn_on(self,**kwargs):
        self.coordinator.security.require_unlocked()
        self.coordinator.projector_controller.set_control_enabled(True)
        self.coordinator.publish(projector_control_enabled=True)
    async def async_turn_off(self,**kwargs):
        self.coordinator.projector_controller.set_control_enabled(False)
        self.coordinator.publish(projector_control_enabled=False)
async def async_setup_entry(hass,entry,async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    entities = [ProjectorControlSwitch(coordinator), OSCOutputSafetySwitch(coordinator), EnttecListenSwitch(coordinator)]
    entities.extend(BuilderSwitch(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "switch" and item.enabled)
    entities.extend(BuilderButton(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "button" and item.enabled)
    async_add_entities(entities)
    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    coordinator.ha_builder_callbacks["switch"] = lambda item: async_add_entities([BuilderSwitch(coordinator, item)])
    coordinator.ha_builder_callbacks["button"] = lambda item: async_add_entities([BuilderButton(coordinator, item)])
    coordinator.ha_builder_remove_callbacks = getattr(coordinator, "ha_builder_remove_callbacks", {})
