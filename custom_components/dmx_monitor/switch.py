from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .ha_builder_entities import BuilderSwitch, async_remove_builder_entity
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


class MIDIOutputSafetySwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "MIDI output safety gate"
    _attr_has_entity_name = True
    _attr_icon = "mdi:midi-port"
    def __init__(self, c):
        super().__init__(c); self._attr_unique_id = "midi_output_safety_gate"
    @property
    def is_on(self): return bool(self.coordinator.midi_output.enabled)
    async def async_turn_on(self, **kwargs):
        self.coordinator.security.require_unlocked()
        self.coordinator.midi_output.set_enabled(True)
        self.coordinator.publish(midi_output=self.coordinator.midi_output.snapshot(), midi_output_sent=self.coordinator.midi_output.sent)
    async def async_turn_off(self, **kwargs):
        self.coordinator.midi_output.set_enabled(False)
        self.coordinator.publish(midi_output=self.coordinator.midi_output.snapshot(), midi_output_sent=self.coordinator.midi_output.sent)

class ShowControlSafetySwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "Show Control safety gate"
    _attr_has_entity_name = True
    _attr_icon = "mdi:play-box-multiple"
    def __init__(self, c):
        super().__init__(c); self._attr_unique_id = "show_control_safety_gate"
    @property
    def is_on(self): return bool(self.coordinator.show_control.enabled)
    async def async_turn_on(self, **kwargs):
        self.coordinator.security.require_unlocked()
        self.coordinator.show_control.enabled = True
        self.coordinator.publish(**self.coordinator.show_control.snapshot())
    async def async_turn_off(self, **kwargs):
        self.coordinator.show_control.enabled = False
        self.coordinator.publish(**self.coordinator.show_control.snapshot())

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

class DmxSceneOutputSafetySwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "DMX scene output safety gate"
    _attr_has_entity_name = True
    _attr_icon = "mdi:palette-swatch"
    def __init__(self, c):
        super().__init__(c); self._attr_unique_id = "dmx_scene_output_safety_gate"
    @property
    def is_on(self): return bool(self.coordinator.dmx_scene_bank.enabled)
    async def async_turn_on(self, **kwargs):
        self.coordinator.security.require_unlocked()
        self.coordinator.dmx_scene_bank.set_enabled(True)
        self.coordinator.publish(**self.coordinator.dmx_scene_bank.snapshot())
    async def async_turn_off(self, **kwargs):
        self.coordinator.dmx_scene_bank.set_enabled(False)
        self.coordinator.publish(**self.coordinator.dmx_scene_bank.snapshot())

async def async_setup_entry(hass,entry,async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    entities = [ProjectorControlSwitch(coordinator), OSCOutputSafetySwitch(coordinator), EnttecListenSwitch(coordinator), FixtureControlSafetySwitch(coordinator), DmxSceneOutputSafetySwitch(coordinator), MIDIOutputSafetySwitch(coordinator), ShowControlSafetySwitch(coordinator)]
    builder_entities = [BuilderSwitch(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "switch" and item.enabled]
    entities.extend(builder_entities)
    async_add_entities(entities)
    live_builder_switches = {e.item_id: e for e in builder_entities}
    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    def _add_switch(item):
        e = BuilderSwitch(coordinator, item)
        live_builder_switches[item.item_id] = e
        async_add_entities([e])
    coordinator.ha_builder_callbacks["switch"] = _add_switch
    # "button" items are owned by button.py's own async_setup_entry, not by
    # this module. They used to be added here via the switch platform's
    # async_add_entities, which registered them under the switch.* domain
    # instead of button.* -- so switch.turn_off was called on a
    # BuilderButton, which has no async_turn_off (audit-confirmed:
    # 'BuilderButton' object has no attribute 'async_turn_off').
    coordinator.ha_builder_remove_callbacks = getattr(coordinator, "ha_builder_remove_callbacks", {})
    async def _remove_switch(item_id):
        entity = live_builder_switches.pop(item_id, None)
        if entity is not None:
            await async_remove_builder_entity(hass, "switch", entity)
    coordinator.ha_builder_remove_callbacks["switch"] = _remove_switch

class FixtureControlSafetySwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "GDTF fixture control safety gate"
    _attr_has_entity_name = True
    _attr_icon = "mdi:spotlight-beam"
    def __init__(self, c):
        super().__init__(c); self._attr_unique_id = "gdtf_fixture_control_safety_gate"
    @property
    def is_on(self): return bool(self.coordinator.fixture_control.control_enabled)
    async def async_turn_on(self, **kwargs):
        self.coordinator.security.require_unlocked()
        self.coordinator.fixture_control.set_control_enabled(True)
        self.coordinator.publish(**self.coordinator.fixture_control.snapshot())
    async def async_turn_off(self, **kwargs):
        self.coordinator.fixture_control.set_control_enabled(False)
        self.coordinator.publish(**self.coordinator.fixture_control.snapshot())
