"""Runtime configuration helpers exposed to the Show Network panel.

Only explicit boolean module gates are writable here. Interface addresses,
ports and structured configuration continue to use Home Assistant OptionsFlow.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..const import (
    DOMAIN,
    CONF_DMX_ARTNET_ENABLED,
    CONF_DMX_SACN_ENABLED,
    CONF_MA_ENABLED,
    CONF_OSC_INPUT_ENABLED,
    CONF_MIDI_ENABLED,
    CONF_PUNCHLIGHT_ENABLED,
    CONF_WATCHDOG_ENABLED,
    CONF_HA_BUILDER_ENABLED,
    CONF_NOTIFICATION_ENABLED,
    CONF_CHAOS_ENABLED,
    CONF_PROJECTOR_MONITOR_ENABLED,
    CONF_UNIVERSES,
)

MODULE_KEYS = {
    "artnet": CONF_DMX_ARTNET_ENABLED,
    "sacn": CONF_DMX_SACN_ENABLED,
    "ma_net3": CONF_MA_ENABLED,
    "osc_input": CONF_OSC_INPUT_ENABLED,
    "midi_input": CONF_MIDI_ENABLED,
    "punchlight": CONF_PUNCHLIGHT_ENABLED,
    "watchdog": CONF_WATCHDOG_ENABLED,
    "ha_builder": CONF_HA_BUILDER_ENABLED,
    "notifications": CONF_NOTIFICATION_ENABLED,
    "diagnostics": CONF_CHAOS_ENABLED,
    "projector_monitor": CONF_PROJECTOR_MONITOR_ENABLED,
}


def _entry_for_call(hass: HomeAssistant, call):
    requested = call.data.get("entry_id")
    entries = hass.config_entries.async_entries(DOMAIN)
    if requested:
        entry = next((item for item in entries if item.entry_id == str(requested)), None)
        if entry is None:
            raise ValueError(f"Unknown config entry: {requested}")
        return entry
    if len(entries) == 1:
        return entries[0]
    raise ValueError("entry_id is required when multiple Show Network entries are configured")


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "set_module_enabled"):
        return

    async def _set_module_enabled(call):
        module = str(call.data.get("module", "")).strip().lower()
        key = MODULE_KEYS.get(module)
        if key is None:
            raise ValueError(f"Unsupported Show Network module gate: {module}")
        entry = _entry_for_call(hass, call)
        new_options = dict(entry.options)
        new_options[key] = bool(call.data.get("enabled", False))
        hass.config_entries.async_update_entry(entry, options=new_options)
        await hass.config_entries.async_reload(entry.entry_id)

    async def _set_dmx_universes(call):
        raw = str(call.data.get("universes", "")).strip()
        if not raw:
            raise ValueError("universes is required")
        values = set()
        for part in raw.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = (int(x) for x in part.split("-", 1))
                if a > b: a, b = b, a
                if a < 1 or b > 63999 or b-a > 2048:
                    raise ValueError("invalid universe range")
                values.update(range(a, b + 1))
            else:
                n = int(part)
                if n < 1 or n > 63999: raise ValueError("invalid universe")
                values.add(n)
        if not values or len(values) > 2048:
            raise ValueError("invalid universe selection")
        entry = _entry_for_call(hass, call)
        new_options = dict(entry.options)
        new_options[CONF_UNIVERSES] = raw
        hass.config_entries.async_update_entry(entry, options=new_options)
        await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(DOMAIN, "set_module_enabled", _set_module_enabled)
    hass.services.async_register(DOMAIN, "set_dmx_universes", _set_dmx_universes)
