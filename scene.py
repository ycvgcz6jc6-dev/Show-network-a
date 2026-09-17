"""Home Assistant Scene entities backed by Show Network DMX scenes."""
from __future__ import annotations

from homeassistant.components.scene import Scene
from .const import DOMAIN


class ShowNetworkDmxScene(Scene):
    _attr_icon = "mdi:palette-swatch"

    def __init__(self, coordinator, scene_id: str):
        self.coordinator = coordinator
        self.scene_id = scene_id
        scene = coordinator.dmx_scene_bank.scenes[scene_id]
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in scene_id).strip("_")
        self._attr_unique_id = f"dmx_scene_{safe}"
        self._attr_name = f"DMX {scene.name}"

    @property
    def available(self):
        return self.scene_id in self.coordinator.dmx_scene_bank.scenes

    @property
    def extra_state_attributes(self):
        bank = self.coordinator.dmx_scene_bank
        scene = bank.scenes.get(self.scene_id)
        return {
            "show_network_dmx_scene": True,
            "scene_id": self.scene_id,
            "active": bank.active_scene_id == self.scene_id,
            "output_enabled": bank.enabled,
            "protocol": bank.output.protocol,
            "universe": bank.output.universe,
            "active_channels": sum(1 for value in scene.values if value) if scene else None,
            "external_override": bank.external_active(),
            "external_source": bank.external_source,
            "external_protocol": bank.external_protocol,
            "resume_delay_s": bank.output.external_hold_s,
        }

    async def async_activate(self, **kwargs) -> None:
        self.coordinator.security.require_unlocked()
        await self.coordinator.dmx_scene_bank.recall(self.scene_id)
        self.coordinator.publish(**self.coordinator.dmx_scene_bank.snapshot())
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    seen: set[str] = set()

    def refresh():
        entities = []
        for scene_id in c.dmx_scene_bank.scenes:
            if scene_id not in seen:
                seen.add(scene_id)
                entities.append(ShowNetworkDmxScene(c, scene_id))
        if entities:
            async_add_entities(entities)

    refresh()
    c.dmx_scene_refresh_callback = refresh
