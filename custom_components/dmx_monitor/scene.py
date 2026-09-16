"""Scene entities for Show Network: the DMX scene bank (dmx_scene_bank.py).

Each stored DmxScene becomes a native Home Assistant scene; activating it
calls the bank's own recall(scene_id) -- already gated by the scene bank's
own output-armed state (see dmx_scene_bank.py), nothing new here.

Show Control cues (show_control.py) are deliberately NOT exposed here: a
theatrical cue stack ("GO to the next cue") does not fit HA's idempotent
"activate this fixed scene" model. Use the show_control_go service instead.
"""
from __future__ import annotations

from homeassistant.components.scene import Scene
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class DmxSceneEntity(CoordinatorEntity, Scene):
    _attr_has_entity_name = True

    def __init__(self, coordinator, scene_id: str) -> None:
        super().__init__(coordinator)
        self.scene_id = scene_id
        self._attr_unique_id = f"show_network_dmx_scene_{scene_id}"

    @property
    def name(self) -> str:
        scene = self.coordinator.dmx_scene_bank.scenes.get(self.scene_id)
        return scene.name if scene else self.scene_id

    @property
    def available(self) -> bool:
        return self.scene_id in self.coordinator.dmx_scene_bank.scenes

    @property
    def extra_state_attributes(self):
        scene = self.coordinator.dmx_scene_bank.scenes.get(self.scene_id)
        return scene.public() if scene else {}

    async def async_activate(self, **kwargs) -> None:
        await self.coordinator.dmx_scene_bank.recall(self.scene_id)
        self.coordinator.publish(**self.coordinator.dmx_scene_bank.snapshot())


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    seen: set[str] = set()

    def _sync_scenes() -> None:
        new_ids = [sid for sid in coordinator.dmx_scene_bank.scenes if sid not in seen]
        if not new_ids:
            return
        seen.update(new_ids)
        async_add_entities([DmxSceneEntity(coordinator, sid) for sid in new_ids])

    _sync_scenes()
    coordinator.dmx_scene_bank_refresh_callback = _sync_scenes
