"""Button platform for Show Network's HA Builder.

This module used to not exist: HA Builder "button" items were added through
switch.py's async_add_entities instead, which registers entities under the
switch.* domain rather than button.*. That mismatch is what produced the
audit-confirmed failure where a HA Builder item created with
entity_type="button" showed up as switch.<id>=unknown and calling
switch.turn_off on it raised 'BuilderButton' object has no attribute
'async_turn_off' -- ButtonEntity has async_press, not async_turn_on/off.
"""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from .const import DOMAIN
from .ha_builder_entities import BuilderButton, async_remove_builder_entity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        BuilderButton(coordinator, item)
        for item in coordinator.ha_builder.items.values()
        if item.entity_type == "button" and item.enabled
    ]
    async_add_entities(entities)
    live_builder_buttons = {e.item_id: e for e in entities}
    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    def _add_button(item):
        e = BuilderButton(coordinator, item)
        live_builder_buttons[item.item_id] = e
        async_add_entities([e])
    coordinator.ha_builder_callbacks["button"] = _add_button
    coordinator.ha_builder_remove_callbacks = getattr(coordinator, "ha_builder_remove_callbacks", {})
    async def _remove_button(item_id):
        entity = live_builder_buttons.pop(item_id, None)
        if entity is not None:
            await async_remove_builder_entity(hass, "button", entity)
    coordinator.ha_builder_remove_callbacks["button"] = _remove_button
