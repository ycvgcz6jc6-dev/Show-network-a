"""Show Control cue service handlers."""
from __future__ import annotations

import asyncio
from homeassistant.core import HomeAssistant
from ..const import DOMAIN
from ..show_control import ShowControlCue


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "fire_show_control_cue"):
        return

    def _c():
        return next(iter(hass.data[DOMAIN].values()))["coordinator"]

    async def _set_enabled(call):
        c = _c()
        if bool(call.data["enabled"]):
            c.security.require_unlocked()
        c.show_control.enabled = bool(call.data["enabled"])
        c.publish(**c.show_control.snapshot())

    async def _upsert(call):
        c = _c(); c.security.require_unlocked()
        cue = ShowControlCue(str(call.data["cue_id"]), str(call.data.get("name") or call.data["cue_id"]), list(call.data.get("actions") or []), bool(call.data.get("enabled", True)))
        c.show_control.upsert(cue)
        await asyncio.to_thread(c.show_control.save)
        c.publish(**c.show_control.snapshot())

    async def _remove(call):
        c = _c(); c.security.require_unlocked()
        c.show_control.remove(str(call.data["cue_id"]))
        await asyncio.to_thread(c.show_control.save)
        c.publish(**c.show_control.snapshot())

    async def _fire(call):
        c = _c(); c.security.require_unlocked()
        if not c.show_control.enabled:
            raise RuntimeError("Show Control safety gate is disabled")
        cue = c.show_control.cues.get(str(call.data["cue_id"]))
        if cue is None or not cue.enabled:
            raise ValueError("Unknown or disabled Show Control cue")
        try:
            for action in cue.actions:
                delay = float(action.get("delay_s", 0.0))
                if delay:
                    await asyncio.sleep(delay)
                typ = action["type"]
                if typ == "ha_service":
                    domain, service = str(action["service"]).split(".", 1)
                    await hass.services.async_call(domain, service, dict(action.get("data") or {}), blocking=True)
                elif typ == "osc":
                    target = c.osc_targets.get(str(action["target_id"]))
                    if target is None: raise ValueError("Unknown OSC target")
                    c.osc_output.send(target, str(action["address"]), list(action.get("args") or []))
                elif typ == "midi":
                    target = c.midi_targets.get(str(action["target_id"]))
                    if target is None: raise ValueError("Unknown MIDI target")
                    await c.midi_output.async_send(target, str(action["message_type"]), dict(action.get("data") or {}))
                elif typ == "dmx_scene":
                    await c.dmx_scene_bank.recall(str(action["scene_id"]))
            c.show_control.fired += 1
            c.show_control.last_cue = cue.cue_id
            c.show_control.last_error = None
        except Exception as exc:
            c.show_control.errors += 1
            c.show_control.last_error = str(exc)
            raise
        finally:
            c.publish(**c.show_control.snapshot(), midi_output=c.midi_output.snapshot(), midi_output_sent=c.midi_output.sent)
            c.publish_osc_status()

    hass.services.async_register(DOMAIN, "set_show_control_enabled", _set_enabled)
    hass.services.async_register(DOMAIN, "upsert_show_control_cue", _upsert)
    hass.services.async_register(DOMAIN, "remove_show_control_cue", _remove)
    hass.services.async_register(DOMAIN, "fire_show_control_cue", _fire)
