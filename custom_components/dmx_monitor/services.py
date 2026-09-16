"""Home Assistant services for Show Network.

Show Network is a single-instance "hub" integration (config_flow.py uses a
fixed unique_id), so every service here operates on the one coordinator
found in ``hass.data[DOMAIN]`` rather than requiring a target entry_id.

Every handler only ever calls an already-existing, already-gated
coordinator method (set_light_sync_enabled, set_osc_output_enabled,
show_control_go, etc.) -- this module adds no new control logic of its own,
only the Home Assistant service registration/schema layer on top of logic
that already exists elsewhere in this codebase.
"""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .dmx_ha_zones import DmxHAZone

_LOGGER = logging.getLogger(__name__)


def _get_coordinator(hass: HomeAssistant):
    for data in hass.data.get(DOMAIN, {}).values():
        if isinstance(data, dict) and data.get("coordinator") is not None:
            return data["coordinator"]
    return None


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "security_unlock"):
        return  # already registered (e.g. a second config entry reload)

    def _require_coordinator(call: ServiceCall):
        coordinator = _get_coordinator(hass)
        if coordinator is None:
            raise RuntimeError("Show Network is not set up yet")
        return coordinator

    # -- Security gate ---------------------------------------------------------
    async def handle_security_unlock(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.security.unlock(reason=call.data.get("reason"), by="service_call")
        coordinator.publish(security=coordinator.security.snapshot())

    async def handle_security_lock(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.security.lock(reason=call.data.get("reason"), by="service_call")
        coordinator.publish(security=coordinator.security.snapshot())

    hass.services.async_register(DOMAIN, "security_unlock", handle_security_unlock, schema=vol.Schema({vol.Optional("reason"): cv.string}))
    hass.services.async_register(DOMAIN, "security_lock", handle_security_lock, schema=vol.Schema({vol.Optional("reason"): cv.string}))

    # -- Active output enable toggles (already security-gated inside coordinator) --
    async def handle_set_light_sync(call: ServiceCall) -> None:
        _require_coordinator(call).set_light_sync_enabled(call.data["enabled"])

    async def handle_set_osc_output(call: ServiceCall) -> None:
        _require_coordinator(call).set_osc_output_enabled(call.data["enabled"])

    hass.services.async_register(DOMAIN, "set_light_sync_enabled", handle_set_light_sync, schema=vol.Schema({vol.Required("enabled"): cv.boolean}))
    hass.services.async_register(DOMAIN, "set_osc_output_enabled", handle_set_osc_output, schema=vol.Schema({vol.Required("enabled"): cv.boolean}))

    # -- Chaos/reliability testing ------------------------------------------------
    async def handle_simulate_signal_loss(call: ServiceCall) -> None:
        await _require_coordinator(call).simulate_signal_loss(call.data.get("key"))

    async def handle_simulate_signal_restore(call: ServiceCall) -> None:
        await _require_coordinator(call).simulate_signal_restore(call.data.get("key"))

    async def handle_simulate_ptp_drift(call: ServiceCall) -> None:
        _require_coordinator(call).simulate_ptp_drift(call.data["offset_ms"])

    async def handle_clear_chaos(call: ServiceCall) -> None:
        _require_coordinator(call).clear_chaos()

    hass.services.async_register(DOMAIN, "simulate_signal_loss", handle_simulate_signal_loss, schema=vol.Schema({vol.Optional("key"): cv.string}))
    hass.services.async_register(DOMAIN, "simulate_signal_restore", handle_simulate_signal_restore, schema=vol.Schema({vol.Optional("key"): cv.string}))
    hass.services.async_register(DOMAIN, "simulate_ptp_drift", handle_simulate_ptp_drift, schema=vol.Schema({vol.Required("offset_ms"): vol.Coerce(float)}))
    hass.services.async_register(DOMAIN, "clear_chaos", handle_clear_chaos, schema=vol.Schema({}))

    # -- Capacity configuration ----------------------------------------------------
    async def handle_set_capacity_config(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.set_capacity_config(**{k: v for k, v in call.data.items() if v is not None})

    hass.services.async_register(DOMAIN, "set_capacity_config", handle_set_capacity_config, schema=vol.Schema({
        vol.Optional("link_mbps"): vol.Coerce(float),
        vol.Optional("dante_mbps"): vol.Coerce(float),
        vol.Optional("cameras_mbps"): vol.Coerce(float),
        vol.Optional("st2110_mbps"): vol.Coerce(float),
        vol.Optional("other_mbps"): vol.Coerce(float),
    }))

    # -- DMX value-triggered rules (rules.py + rule_storage.py) ---------------------
    async def handle_save_rules(call: ServiceCall) -> None:
        await _require_coordinator(call).async_save_rules()

    hass.services.async_register(DOMAIN, "save_rules", handle_save_rules, schema=vol.Schema({}))

    # -- DMX -> Home Assistant zones (dmx_ha_zones.py) -------------------------------
    _zone_schema = vol.Schema({
        vol.Required("zone_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("universe"): vol.All(vol.Coerce(int), vol.Range(min=1, max=63999)),
        vol.Optional("entity_ids", default=[]): [cv.entity_id],
        vol.Optional("mode", default="dimmer"): vol.In(["dimmer", "switch", "cct", "rgb", "rgbw"]),
        vol.Optional("channels", default=[1]): [vol.All(vol.Coerce(int), vol.Range(min=1, max=512))],
        vol.Optional("source"): cv.string,
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("min_interval_ms", default=100): vol.Coerce(int),
        vol.Optional("deadband", default=0.0): vol.Coerce(float),
        vol.Optional("invert", default=False): cv.boolean,
        vol.Optional("dimmer_curve", default="linear"): cv.string,
    })

    async def handle_set_dmx_ha_zones(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        zones = []
        for raw_zone in call.data["zones"]:
            zone_data = dict(raw_zone)
            zone_data["entity_ids"] = tuple(zone_data.get("entity_ids", ()))
            zone_data["channels"] = tuple(zone_data.get("channels", (1,)))
            zones.append(DmxHAZone(**zone_data))
        coordinator.set_dmx_ha_zones(zones)

    hass.services.async_register(DOMAIN, "set_dmx_ha_zones", handle_set_dmx_ha_zones, schema=vol.Schema({
        vol.Required("zones"): [_zone_schema],
    }))

    # -- Show Control cue bank --------------------------------------------------------
    async def handle_show_control_go(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        dispatched = coordinator.show_control_go(call.data.get("target"))
        _LOGGER.debug("show_control_go dispatched %d action(s)", dispatched)

    async def handle_show_control_back(call: ServiceCall) -> None:
        _require_coordinator(call).show_control.back()

    async def handle_show_control_reset(call: ServiceCall) -> None:
        _require_coordinator(call).show_control.reset()

    hass.services.async_register(DOMAIN, "show_control_go", handle_show_control_go, schema=vol.Schema({vol.Optional("target"): vol.Any(cv.string, int)}))
    hass.services.async_register(DOMAIN, "show_control_back", handle_show_control_back, schema=vol.Schema({}))
    hass.services.async_register(DOMAIN, "show_control_reset", handle_show_control_reset, schema=vol.Schema({}))

    # -- DMX scene bank (direct recall, independent of Show Control) ----------------
    async def handle_recall_dmx_scene(call: ServiceCall) -> None:
        await _require_coordinator(call).dmx_scene_bank.recall(call.data["scene_id"])

    hass.services.async_register(DOMAIN, "recall_dmx_scene", handle_recall_dmx_scene, schema=vol.Schema({vol.Required("scene_id"): cv.string}))

    # -- DMX scene bank (dmx_scene_bank.py) ------------------------------------------
    async def handle_save_dmx_scene(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.dmx_scene_bank.upsert_scene(call.data["scene_id"], call.data["name"], call.data["values"])
        coordinator.publish(**coordinator.dmx_scene_bank.snapshot())
        refresh = getattr(coordinator, "dmx_scene_bank_refresh_callback", None)
        if refresh:
            refresh()

    async def handle_delete_dmx_scene(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.dmx_scene_bank.delete_scene(call.data["scene_id"])
        coordinator.publish(**coordinator.dmx_scene_bank.snapshot())

    async def handle_configure_dmx_scene_output(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        coordinator.dmx_scene_bank.configure_output(dict(call.data))
        coordinator.publish(**coordinator.dmx_scene_bank.snapshot())

    hass.services.async_register(DOMAIN, "save_dmx_scene", handle_save_dmx_scene, schema=vol.Schema({
        vol.Required("scene_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("values"): [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))],
    }))
    hass.services.async_register(DOMAIN, "delete_dmx_scene", handle_delete_dmx_scene, schema=vol.Schema({vol.Required("scene_id"): cv.string}))
    hass.services.async_register(DOMAIN, "configure_dmx_scene_output", handle_configure_dmx_scene_output, schema=vol.Schema({
        vol.Optional("protocol"): vol.In(["sacn", "artnet", "enttec"]),
        vol.Optional("universe"): vol.Coerce(int),
        vol.Optional("host"): cv.string,
        vol.Optional("port"): vol.Coerce(int),
        vol.Optional("priority"): vol.Coerce(int),
        vol.Optional("enttec_device"): cv.string,
        vol.Optional("external_hold_s"): vol.Coerce(float),
    }))

    # -- Video IP preview bridge polling (tools/video_preview_bridge/video_bridge.py) --
    async def handle_poll_video_preview_bridge(call: ServiceCall) -> None:
        coordinator = _require_coordinator(call)
        attached = await coordinator.video_ip_supervision.async_poll_preview_bridge(call.data["base_url"])
        coordinator.publish(**coordinator.video_ip_supervision.snapshot())
        _LOGGER.debug("Video preview bridge poll attached %d source(s)", attached)

    hass.services.async_register(DOMAIN, "poll_video_preview_bridge", handle_poll_video_preview_bridge, schema=vol.Schema({vol.Required("base_url"): cv.string}))
