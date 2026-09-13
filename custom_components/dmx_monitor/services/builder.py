"""Show Network builder service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "ha_builder_create"):
        async def _ha_builder_create(call):
            c = coordinator_for_call(hass, call)
            if not c.ha_builder_enabled:
                raise ValueError("HA Builder est désactivé")
            item = c.ha_builder.create(
                name=str(call.data["name"]), entity_type=str(call.data.get("entity_type", "switch")),
                item_id=call.data.get("item_id"), device_class=call.data.get("device_class"),
                unit=call.data.get("unit"), icon=call.data.get("icon"), area=call.data.get("area"),
                enabled=bool(call.data.get("enabled", True)), state=call.data.get("state"),
                min_value=call.data.get("min_value"), max_value=call.data.get("max_value"), step=call.data.get("step"),
            )
            c.data["ha_builder"] = c.ha_builder.snapshot()
            c.publish(ha_builder=c.data["ha_builder"])
            c.archive.record("ha", "builder_entity_created", {"item_id": item.item_id, "entity_type": item.entity_type, "name": item.name}) if c.archive else None
            callbacks = getattr(c, "ha_builder_callbacks", {})
            cb = callbacks.get(item.entity_type)
            if cb:
                cb(item)
        async def _ha_builder_remove(call):
            c = coordinator_for_call(hass, call)
            item_id = str(call.data["item_id"])
            item = c.ha_builder.items.get(item_id)
            c.ha_builder.remove(item_id)
            c.data["ha_builder"] = c.ha_builder.snapshot()
            c.publish(ha_builder=c.data["ha_builder"])
            if c.archive:
                c.archive.record("ha", "builder_entity_removed", {"item_id": item_id})
            callbacks = getattr(c, "ha_builder_remove_callbacks", {})
            for cb in callbacks.values():
                cb(item_id)
        async def _ha_builder_set_state(call):
            c = coordinator_for_call(hass, call)
            c.ha_builder.set_state(str(call.data["item_id"]), call.data.get("state"))
            c.data["ha_builder"] = c.ha_builder.snapshot()
            c.publish(ha_builder=c.data["ha_builder"])
        hass.services.async_register(DOMAIN, "ha_builder_create", _ha_builder_create)
        hass.services.async_register(DOMAIN, "ha_builder_remove", _ha_builder_remove)
        hass.services.async_register(DOMAIN, "ha_builder_set_state", _ha_builder_set_state)
