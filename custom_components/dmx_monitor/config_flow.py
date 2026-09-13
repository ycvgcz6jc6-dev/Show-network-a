from __future__ import annotations

import asyncio
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .enttec import discover_ports
from .punchlight import PunchLightState
from .midi_runtime import MIDIInputRuntime
from .network_interfaces import snapshot as network_interface_snapshot
from .const import (
    DOMAIN, CONF_INTERFACE, CONF_UNIVERSES, CONF_THRESHOLD, CONF_LANGUAGE,
    CONF_GIGACORE_HOSTS, CONF_GIGACORE_COMMUNITY, DEFAULT_GIGACORE_COMMUNITY,
    CONF_ENTTEC_DEVICE, CONF_ENTTEC_MODEL,
    CONF_WATCHDOG_ENABLED, CONF_WATCHDOG_PROTOCOL, CONF_WATCHDOG_UNIVERSE,
    CONF_WATCHDOG_SOURCE, CONF_WATCHDOG_TIMEOUT, CONF_WATCHDOG_RECOVERY_DELAY,
    CONF_WATCHDOG_LOSS_SCENE, CONF_WATCHDOG_RECOVERY_SCENE,
    CONF_PUNCHLIGHT_ENABLED, CONF_PUNCHLIGHT_DEVICE, CONF_PUNCHLIGHT_RECORD_SCENE,
    CONF_PUNCHLIGHT_STOP_SCENE, CONF_PUNCHLIGHT_READY_SCENE, CONF_PUNCHLIGHT_NOT_READY_SCENE,
    CONF_ARCHIVE_DESTINATION, CONF_ARCHIVE_RETENTION_DAYS, CONF_ARCHIVE_MAX_BYTES,
    CONF_CAPACITY_LINK_MBPS, CONF_CAPACITY_DANTE_MBPS, CONF_CAPACITY_CAMERAS_MBPS,
    CONF_CAPACITY_ST2110_MBPS, CONF_CAPACITY_OTHER_MBPS,
    CONF_INTERFACE_DMX, CONF_INTERFACE_DANTE, CONF_INTERFACE_PTP,
    CONF_INTERFACE_MA, CONF_INTERFACE_AUDIO, CONF_AES70_HOSTS, CONF_AES70_PORT, CONF_NOTIFICATION_ENABLED, CONF_OSC_INPUT_ENABLED, CONF_OSC_INPUT_PORT, CONF_OSC_INPUT_INTERFACE, CONF_MIDI_ENABLED, CONF_MIDI_DEVICE,
    CONF_NOTIFICATION_TARGET, CONF_NOTIFICATION_MODE, CONF_HA_BUILDER_ENABLED,
    CONF_PERFORMANCE_PROFILE, PERFORMANCE_PROFILES,
)


def _notification_choices(hass, current: str = "") -> list[str]:
    choices = ["persistent"]
    for service in hass.services.async_services().get("notify", {}):
        value = f"notify.{service}"
        if value not in choices:
            choices.append(value)
    if current and current not in choices:
        choices.append(current)
    return choices


def _interface_choices(rows: list[dict] | None = None) -> list[str]:
    values = ["0.0.0.0"]
    for row in rows or []:
        for addr in row.get("addresses", []):
            if addr and addr not in values and ":" not in addr:
                values.append(addr)
    return values


def _interface_schema(key: str, choices: list[str], default: str = "0.0.0.0"):
    return {vol.Optional(key, default=default): vol.In(choices)}


class DmxMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def _async_form_choices(self):
        rows, enttec_ports, midi_ports = await asyncio.gather(
            self.hass.async_add_executor_job(network_interface_snapshot),
            self.hass.async_add_executor_job(discover_ports),
            self.hass.async_add_executor_job(MIDIInputRuntime.list_input_ports),
        )
        return _interface_choices(rows), [p.device for p in enttec_ports], midi_ports

    async def async_step_reconfigure(self, user_input=None):
        """Reconfigure the existing Show Network hub without creating a second entry."""
        entry = self._get_reconfigure_entry()
        await self.async_set_unique_id(entry.unique_id or "show_network")
        self._abort_if_unique_id_mismatch()
        choices, enttec_ports, punchlight_ports = await self._async_form_choices()
        current = {**entry.data, **entry.options}
        if user_input is not None:
            data = dict(user_input)
            raw_projectors = data.get("projectors", "")
            if raw_projectors:
                try:
                    data["projectors"] = json.loads(raw_projectors)
                    if not isinstance(data["projectors"], list):
                        raise ValueError
                except Exception:
                    return self.async_show_form(
                        step_id="reconfigure",
                        data_schema=self._schema({**current, **user_input}, choices, enttec_ports, punchlight_ports),
                        errors={"projectors": "invalid_json"},
                    )
            else:
                data["projectors"] = []
            data.setdefault(CONF_INTERFACE, data.get(CONF_INTERFACE_DMX, "0.0.0.0"))
            return self.async_update_reload_and_abort(entry, data_updates=data)
        defaults = dict(current)
        if isinstance(defaults.get("projectors"), list):
            defaults["projectors"] = json.dumps(defaults["projectors"])
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(defaults, choices, enttec_ports, punchlight_ports),
        )

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("show_network")
        self._abort_if_unique_id_configured()
        choices, enttec_ports, punchlight_ports = await self._async_form_choices()
        if user_input is not None:
            data = dict(user_input)
            raw_projectors = data.get("projectors", "")
            if raw_projectors:
                try:
                    data["projectors"] = json.loads(raw_projectors)
                    if not isinstance(data["projectors"], list):
                        raise ValueError
                except Exception:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._schema(user_input, choices, enttec_ports, punchlight_ports),
                        errors={"projectors": "invalid_json"},
                    )
            else:
                data["projectors"] = []
            data.setdefault(CONF_INTERFACE, data.get(CONF_INTERFACE_DMX, "0.0.0.0"))
            return self.async_create_entry(title="Show Network", data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input, choices, enttec_ports, punchlight_ports),
        )

    def _schema(self, user_input=None, choices=None, enttec_ports=None, punchlight_ports=None):
        choices = choices or ["0.0.0.0"]
        enttec_ports = enttec_ports or []
        punchlight_ports = punchlight_ports or []
        return vol.Schema({
            vol.Required(CONF_INTERFACE, default="0.0.0.0"): vol.In(choices),
            **_interface_schema(CONF_INTERFACE_DMX, choices),
            **_interface_schema(CONF_INTERFACE_DANTE, choices),
            **_interface_schema(CONF_INTERFACE_PTP, choices),
            **_interface_schema(CONF_INTERFACE_MA, choices),
            **_interface_schema(CONF_INTERFACE_AUDIO, choices),
            vol.Required(CONF_UNIVERSES, default="1-16"): str,
            vol.Required(CONF_THRESHOLD, default=10): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.Required(CONF_LANGUAGE, default="auto"): vol.In(["auto", "fr", "en", "es", "it", "nl", "de"]),
            vol.Optional(CONF_PERFORMANCE_PROFILE, default="auto"): vol.In(PERFORMANCE_PROFILES),
            vol.Optional(CONF_GIGACORE_HOSTS, default=""): str,
            vol.Optional(CONF_AES70_HOSTS, default=""): str,
            vol.Optional(CONF_AES70_PORT, default=65000): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(CONF_GIGACORE_COMMUNITY, default=DEFAULT_GIGACORE_COMMUNITY): str,
            vol.Optional(CONF_ENTTEC_DEVICE, default=""): vol.In([""] + enttec_ports),
            vol.Optional(CONF_ENTTEC_MODEL, default="auto"): vol.In(["auto", "DMX USB Pro", "DMX USB Pro Mk2"]),
            vol.Optional(CONF_OSC_INPUT_ENABLED, default=False): bool,
            vol.Optional(CONF_OSC_INPUT_INTERFACE, default="0.0.0.0"): vol.In(choices),
            vol.Optional(CONF_OSC_INPUT_PORT, default=8000): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
            vol.Optional(CONF_MIDI_ENABLED, default=False): bool,
            vol.Optional(CONF_MIDI_DEVICE, default=""): vol.In([""] + punchlight_ports),
            vol.Optional(CONF_PUNCHLIGHT_ENABLED, default=False): bool,
            vol.Optional(CONF_PUNCHLIGHT_DEVICE, default=""): vol.In([""] + punchlight_ports),
            vol.Optional(CONF_PUNCHLIGHT_RECORD_SCENE, default=""): str,
            vol.Optional(CONF_PUNCHLIGHT_STOP_SCENE, default=""): str,
            vol.Optional(CONF_PUNCHLIGHT_READY_SCENE, default=""): str,
            vol.Optional(CONF_PUNCHLIGHT_NOT_READY_SCENE, default=""): str,
            vol.Optional(CONF_WATCHDOG_ENABLED, default=False): bool,
            vol.Optional(CONF_WATCHDOG_PROTOCOL, default="ENTTEC"): vol.In(["ENTTEC", "sACN", "Art-Net"]),
            vol.Optional(CONF_WATCHDOG_UNIVERSE, default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=63999)),
            vol.Optional(CONF_WATCHDOG_SOURCE, default=""): str,
            vol.Optional(CONF_WATCHDOG_TIMEOUT, default=10): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=3600)),
            vol.Optional(CONF_WATCHDOG_RECOVERY_DELAY, default=3): vol.All(vol.Coerce(float), vol.Range(min=0, max=3600)),
            vol.Optional(CONF_WATCHDOG_LOSS_SCENE, default=""): str,
            vol.Optional(CONF_WATCHDOG_RECOVERY_SCENE, default=""): str,
            vol.Optional("switch_manufacturers", default=["luminex", "elc", "green_go"]): vol.All([str]),
            vol.Optional(CONF_ARCHIVE_DESTINATION, default="show_network_archive"): str,
            vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
            vol.Optional(CONF_NOTIFICATION_TARGET, default="persistent"): vol.In(_notification_choices(self.hass)),
            vol.Optional(CONF_NOTIFICATION_MODE, default="both"): vol.In(["notify", "persistent", "both"]),
            vol.Optional(CONF_HA_BUILDER_ENABLED, default=True): bool,
            vol.Optional(CONF_ARCHIVE_RETENTION_DAYS, default=30): vol.All(vol.Coerce(int), vol.Range(min=1, max=3650)),
            vol.Optional(CONF_ARCHIVE_MAX_BYTES, default=5 * 1024 * 1024): vol.All(vol.Coerce(int), vol.Range(min=256000, max=100 * 1024 * 1024)),
            vol.Optional(CONF_CAPACITY_LINK_MBPS, default=1000): vol.All(vol.Coerce(float), vol.Range(min=10, max=100000)),
            vol.Optional(CONF_CAPACITY_DANTE_MBPS, default=0): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_CAMERAS_MBPS, default=0): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_ST2110_MBPS, default=0): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_OTHER_MBPS, default=0): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional("projectors", default=""): str,
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DmxMonitorOptionsFlow(config_entry)


class DmxMonitorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def _async_form_choices(self):
        rows, enttec_ports, midi_ports = await asyncio.gather(
            self.hass.async_add_executor_job(network_interface_snapshot),
            self.hass.async_add_executor_job(discover_ports),
            self.hass.async_add_executor_job(MIDIInputRuntime.list_input_ports),
        )
        return _interface_choices(rows), [p.device for p in enttec_ports], midi_ports

    async def async_step_init(self, user_input=None):
        choices, enttec_ports, punchlight_ports = await self._async_form_choices()
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        source = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_INTERFACE, default=source.get(CONF_INTERFACE, "0.0.0.0")): vol.In(choices),
            **_interface_schema(CONF_INTERFACE_DMX, choices, source.get(CONF_INTERFACE_DMX, source.get(CONF_INTERFACE, "0.0.0.0"))),
            **_interface_schema(CONF_INTERFACE_DANTE, choices, source.get(CONF_INTERFACE_DANTE, source.get(CONF_INTERFACE, "0.0.0.0"))),
            **_interface_schema(CONF_INTERFACE_PTP, choices, source.get(CONF_INTERFACE_PTP, source.get(CONF_INTERFACE, "0.0.0.0"))),
            **_interface_schema(CONF_INTERFACE_MA, choices, source.get(CONF_INTERFACE_MA, source.get(CONF_INTERFACE, "0.0.0.0"))),
            **_interface_schema(CONF_INTERFACE_AUDIO, choices, source.get(CONF_INTERFACE_AUDIO, source.get(CONF_INTERFACE, "0.0.0.0"))),
            vol.Optional(CONF_AES70_HOSTS, default=source.get(CONF_AES70_HOSTS, "")): str,
            vol.Optional(CONF_AES70_PORT, default=source.get(CONF_AES70_PORT, 65000)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(CONF_ENTTEC_DEVICE, default=source.get(CONF_ENTTEC_DEVICE, "")): vol.In([""] + enttec_ports),
            vol.Optional(CONF_ENTTEC_MODEL, default=source.get(CONF_ENTTEC_MODEL, "auto")): vol.In(["auto", "DMX USB Pro", "DMX USB Pro Mk2"]),
            vol.Optional(CONF_OSC_INPUT_ENABLED, default=source.get(CONF_OSC_INPUT_ENABLED, False)): bool,
            vol.Optional(CONF_OSC_INPUT_INTERFACE, default=source.get(CONF_OSC_INPUT_INTERFACE, "0.0.0.0")): vol.In(choices),
            vol.Optional(CONF_OSC_INPUT_PORT, default=source.get(CONF_OSC_INPUT_PORT, 8000)): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
            vol.Optional(CONF_MIDI_ENABLED, default=source.get(CONF_MIDI_ENABLED, False)): bool,
            vol.Optional(CONF_MIDI_DEVICE, default=source.get(CONF_MIDI_DEVICE, "")): vol.In([""] + punchlight_ports),
            vol.Optional(CONF_PUNCHLIGHT_ENABLED, default=source.get(CONF_PUNCHLIGHT_ENABLED, False)): bool,
            vol.Optional(CONF_PUNCHLIGHT_DEVICE, default=source.get(CONF_PUNCHLIGHT_DEVICE, "")): vol.In([""] + punchlight_ports),
            vol.Optional(CONF_PUNCHLIGHT_RECORD_SCENE, default=source.get(CONF_PUNCHLIGHT_RECORD_SCENE, "")): str,
            vol.Optional(CONF_PUNCHLIGHT_STOP_SCENE, default=source.get(CONF_PUNCHLIGHT_STOP_SCENE, "")): str,
            vol.Optional(CONF_PUNCHLIGHT_READY_SCENE, default=source.get(CONF_PUNCHLIGHT_READY_SCENE, "")): str,
            vol.Optional(CONF_PUNCHLIGHT_NOT_READY_SCENE, default=source.get(CONF_PUNCHLIGHT_NOT_READY_SCENE, "")): str,
            vol.Required(CONF_THRESHOLD, default=source.get(CONF_THRESHOLD, 10)): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.Required(CONF_LANGUAGE, default=source.get(CONF_LANGUAGE, "auto")): vol.In(["auto", "fr", "en", "es", "it", "nl", "de"]),
            vol.Optional(CONF_PERFORMANCE_PROFILE, default=source.get(CONF_PERFORMANCE_PROFILE, "auto")): vol.In(PERFORMANCE_PROFILES),
            vol.Optional(CONF_ARCHIVE_DESTINATION, default=source.get(CONF_ARCHIVE_DESTINATION, "show_network_archive")): str,
            vol.Optional(CONF_NOTIFICATION_ENABLED, default=source.get(CONF_NOTIFICATION_ENABLED, False)): bool,
            vol.Optional(CONF_NOTIFICATION_TARGET, default=source.get(CONF_NOTIFICATION_TARGET, "persistent")): vol.In(_notification_choices(self.hass, source.get(CONF_NOTIFICATION_TARGET, ""))),
            vol.Optional(CONF_NOTIFICATION_MODE, default=source.get(CONF_NOTIFICATION_MODE, "both")): vol.In(["notify", "persistent", "both"]),
            vol.Optional(CONF_HA_BUILDER_ENABLED, default=source.get(CONF_HA_BUILDER_ENABLED, True)): bool,
            vol.Optional(CONF_ARCHIVE_RETENTION_DAYS, default=source.get(CONF_ARCHIVE_RETENTION_DAYS, 30)): vol.All(vol.Coerce(int), vol.Range(min=1, max=3650)),
            vol.Optional(CONF_ARCHIVE_MAX_BYTES, default=source.get(CONF_ARCHIVE_MAX_BYTES, 5 * 1024 * 1024)): vol.All(vol.Coerce(int), vol.Range(min=256000, max=100 * 1024 * 1024)),
            vol.Optional(CONF_CAPACITY_LINK_MBPS, default=source.get(CONF_CAPACITY_LINK_MBPS, 1000)): vol.All(vol.Coerce(float), vol.Range(min=10, max=100000)),
            vol.Optional(CONF_CAPACITY_DANTE_MBPS, default=source.get(CONF_CAPACITY_DANTE_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_CAMERAS_MBPS, default=source.get(CONF_CAPACITY_CAMERAS_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_ST2110_MBPS, default=source.get(CONF_CAPACITY_ST2110_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_CAPACITY_OTHER_MBPS, default=source.get(CONF_CAPACITY_OTHER_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
            vol.Optional(CONF_WATCHDOG_ENABLED, default=source.get(CONF_WATCHDOG_ENABLED, False)): bool,
            vol.Optional(CONF_WATCHDOG_PROTOCOL, default=source.get(CONF_WATCHDOG_PROTOCOL, "ENTTEC")): vol.In(["ENTTEC", "sACN", "Art-Net"]),
            vol.Optional(CONF_WATCHDOG_UNIVERSE, default=source.get(CONF_WATCHDOG_UNIVERSE, 1)): vol.All(vol.Coerce(int), vol.Range(min=1, max=63999)),
            vol.Optional(CONF_WATCHDOG_SOURCE, default=source.get(CONF_WATCHDOG_SOURCE, "")): str,
            vol.Optional(CONF_WATCHDOG_TIMEOUT, default=source.get(CONF_WATCHDOG_TIMEOUT, 10)): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=3600)),
            vol.Optional(CONF_WATCHDOG_RECOVERY_DELAY, default=source.get(CONF_WATCHDOG_RECOVERY_DELAY, 3)): vol.All(vol.Coerce(float), vol.Range(min=0, max=3600)),
            vol.Optional(CONF_WATCHDOG_LOSS_SCENE, default=source.get(CONF_WATCHDOG_LOSS_SCENE, "")): str,
            vol.Optional(CONF_WATCHDOG_RECOVERY_SCENE, default=source.get(CONF_WATCHDOG_RECOVERY_SCENE, "")): str,
            vol.Optional("switch_manufacturers", default=source.get("switch_manufacturers", ["luminex", "elc", "green_go"])): vol.All([str]),
            vol.Optional("projectors", default=json.dumps(source.get("projectors", [])) if isinstance(source.get("projectors", []), list) else source.get("projectors", "")): str,
        }))
