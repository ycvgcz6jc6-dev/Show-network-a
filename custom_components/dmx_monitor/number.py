"""Number entities for GDTF fixture attributes and HA Builder."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .ha_builder_entities import BuilderNumber


class FixtureAttributeNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, patch_id: str, attribute: str, spec: dict):
        super().__init__(coordinator)
        self.patch_id = patch_id
        self.attribute = attribute
        patch = coordinator.fixture_control.patches[patch_id]
        safe_attr = "".join(c.lower() if c.isalnum() else "_" for c in attribute).strip("_")
        self._attr_unique_id = f"gdtf_{patch_id}_{safe_attr}"
        self._attr_name = f"{patch.name} {attribute}"
        self._attr_native_min_value = float(spec.get("min", 0.0))
        self._attr_native_max_value = float(spec.get("max", 100.0))
        span = abs(self._attr_native_max_value - self._attr_native_min_value)
        self._attr_native_step = 0.1 if span <= 360 else 1.0
        self._attr_icon = "mdi:spotlight-beam"

    @property
    def native_value(self):
        patch = self.coordinator.fixture_control.patches.get(self.patch_id)
        if not patch:
            return None
        return patch.values.get(self.attribute)

    @property
    def extra_state_attributes(self):
        patch = self.coordinator.fixture_control.patches.get(self.patch_id)
        if not patch:
            return {"show_network_gdtf": True}
        return {
            "show_network_gdtf": True,
            "patch_id": self.patch_id,
            "attribute": self.attribute,
            "universe": patch.universe,
            "address": patch.address,
            "mode": patch.mode,
            "gdtf_file": patch.gdtf_file,
        }

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.security.require_unlocked()
        self.coordinator.fixture_control.set_attribute(self.patch_id, self.attribute, float(value))
        await self.coordinator.fixture_control.send_now(self.patch_id)
        self.coordinator.publish(**self.coordinator.fixture_control.snapshot())
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    seen: set[str] = set()

    def build_fixture_entities():
        entities = []
        for patch_id in list(c.fixture_control.patches):
            for attribute, spec in c.fixture_control.attributes(patch_id).items():
                uid = f"{patch_id}|{attribute}"
                if uid not in seen:
                    seen.add(uid)
                    entities.append(FixtureAttributeNumber(c, patch_id, attribute, spec))
        if entities:
            async_add_entities(entities)

    build_fixture_entities()
    async_add_entities([BuilderNumber(c, item) for item in c.ha_builder.items.values() if item.entity_type == "number" and item.enabled])
    c.fixture_number_refresh_callback = build_fixture_entities
    c.ha_builder_callbacks = getattr(c, "ha_builder_callbacks", {})
    c.ha_builder_callbacks["number"] = lambda item: async_add_entities([BuilderNumber(c, item)])
