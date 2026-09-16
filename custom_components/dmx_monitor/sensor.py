"""Sensor entities for Show Network.

Follows the exact same structure already established by the real
binary_sensor.py/number.py files: a handful of static summary sensors, plus
the already-existing dynamic sources (projector_platform.sensor_entities,
ha_builder_entities.BuilderSensor) that were simply never wired into a
platform file because sensor.py did not exist.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ha_builder_entities import BuilderSensor
from .projector_platform import sensor_entities as projector_sensor_entities


class _SummarySensor(CoordinatorEntity, SensorEntity):
    """Generic read-only sensor over a coordinator.data path.

    ``path`` is a tuple of dict keys walked from coordinator.data; a missing
    key at any point yields None rather than raising, since coordinator.data
    keys legitimately come and go as optional monitors start/stop.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id: str, name: str, path: tuple[str, ...], *,
                 icon: str | None = None, unit: str | None = None, device_class: str | None = None) -> None:
        super().__init__(coordinator)
        self._path = path
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self):
        value: object = self.coordinator.data
        for key in self._path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value


# (unique_id suffix, display name, data path, icon, unit)
_SUMMARY_SENSORS: tuple[tuple[str, str, tuple[str, ...], str, str | None], ...] = (
    ("dmx_universe_count", "DMX universes actifs", ("dmx_universes",), "mdi:dip-switch", None),
    ("dante_packets", "Dante — paquets reçus", ("dante_packets",), "mdi:audio-video", None),
    ("dante_sources", "Dante — sources", ("dante_sources",), "mdi:audio-video", None),
    ("aes67_sap_sessions", "AES67 — sessions SAP", ("aes67_sap_sessions",), "mdi:waveform", None),
    ("gigacore_status", "GigaCore — état", ("gigacore_status",), "mdi:switch", None),
    ("switch_profiles_enabled", "Switches — profils actifs", ("switch_profiles",), "mdi:switch", None),
    ("rdm_device_count", "RDM — appareils", ("rdm_device_count",), "mdi:remote", None),
    ("etc_cem3_online", "ETC CEM3 — racks en ligne", ("etc_live", "online"), "mdi:power-plug", None),
    ("st2110_rtp_packets", "ST 2110 — paquets RTP", ("st2110_rtp_packets",), "mdi:video-wireless", None),
    ("video_ip_source_count", "Vidéo IP — sources", ("video_ip_source_count",), "mdi:video-input-hdmi", None),
    ("ma_net3_stations", "MA-Net3 — stations", ("ma_net3_stations",), "mdi:tune-vertical", None),
    ("watchdog_active", "Watchdogs — signaux perdus", ("watchdog_active",), "mdi:alarm-light", None),
    ("dmx_rule_count", "Règles DMX — définies", ("dmx_rules",), "mdi:sitemap", None),
    ("show_control_current_number", "Show Control — cue actuelle", ("show_control_current_number",), "mdi:script-text-play", None),
    ("network_capacity_usage_pct", "Réseau — utilisation estimée", ("network_capacity", "estimated_usage_pct"), "mdi:speedometer", "%"),
    ("timecode_formatted", "Timecode", ("timecode_formatted",), "mdi:clock-outline", None),
)


class ShowNetworkSummarySensor(_SummarySensor):
    def __init__(self, coordinator, suffix: str, name: str, path: tuple[str, ...], icon: str, unit: str | None) -> None:
        super().__init__(coordinator, f"show_network_{suffix}", name, path, icon=icon, unit=unit)

    @property
    def native_value(self):
        value = super().native_value
        # Several summary paths point at a list/dict rather than a scalar;
        # a sensor state must be a scalar, so report a count for those while
        # keeping the full structure available as an attribute.
        if isinstance(value, (list, dict)):
            return len(value)
        return value

    @property
    def extra_state_attributes(self):
        value: object = self.coordinator.data
        for key in self._path:
            if not isinstance(value, dict):
                return {}
            value = value.get(key)
        if isinstance(value, dict):
            return {"detail": value}
        if isinstance(value, list):
            return {"detail": value[:50]}  # bounded, avoid a huge attribute payload
        return {}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        ShowNetworkSummarySensor(coordinator, suffix, name, path, icon, unit)
        for suffix, name, path, icon, unit in _SUMMARY_SENSORS
    ]
    entities.extend(projector_sensor_entities(coordinator))
    entities.extend(
        BuilderSensor(coordinator, item)
        for item in coordinator.ha_builder.items.values()
        if item.entity_type == "sensor" and item.enabled
    )
    async_add_entities(entities)

    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    coordinator.ha_builder_callbacks["sensor"] = lambda item: async_add_entities([BuilderSensor(coordinator, item)])
