"""MIDI OUT service handlers."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from homeassistant.core import HomeAssistant
from ..const import DOMAIN
from ..midi_output import MIDITarget


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "send_midi"):
        return

    def _c():
        return next(iter(hass.data[DOMAIN].values()))["coordinator"]

    async def _set_enabled(call):
        c = _c()
        if bool(call.data["enabled"]):
            c.security.require_unlocked()
        c.midi_output.set_enabled(bool(call.data["enabled"]))
        c.publish(midi_output=c.midi_output.snapshot(), midi_output_sent=c.midi_output.sent)

    async def _create_target(call):
        c = _c(); c.security.require_unlocked()
        target = MIDITarget(str(call.data["target_id"]), str(call.data.get("name") or call.data["target_id"]), str(call.data["port_name"]), bool(call.data.get("enabled", True)))
        c.midi_targets[target.target_id] = target
        await asyncio.to_thread(c.midi_target_store.save, list(c.midi_targets.values()))
        c.publish(midi_targets=[asdict(x) for x in c.midi_targets.values()])

    async def _remove_target(call):
        c = _c(); c.security.require_unlocked()
        c.midi_targets.pop(str(call.data["target_id"]), None)
        await asyncio.to_thread(c.midi_target_store.save, list(c.midi_targets.values()))
        c.publish(midi_targets=[asdict(x) for x in c.midi_targets.values()])

    async def _send(call):
        c = _c(); c.security.require_unlocked()
        target = c.midi_targets.get(str(call.data["target_id"]))
        if target is None:
            raise ValueError("Unknown MIDI target")
        data = dict(call.data.get("data") or {})
        await c.midi_output.async_send(target, str(call.data["message_type"]), data)
        c.publish(midi_output=c.midi_output.snapshot(), midi_output_sent=c.midi_output.sent)

    hass.services.async_register(DOMAIN, "set_midi_output_enabled", _set_enabled)
    hass.services.async_register(DOMAIN, "create_midi_target", _create_target)
    hass.services.async_register(DOMAIN, "remove_midi_target", _remove_target)
    hass.services.async_register(DOMAIN, "send_midi", _send)
