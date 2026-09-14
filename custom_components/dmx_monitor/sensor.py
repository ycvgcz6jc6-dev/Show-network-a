"""Read-only Show Network diagnostic sensors."""
from __future__ import annotations

import base64
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .coordinator import ShowNetworkCoordinator
from .entity import ShowNetworkEntity, DOMAIN
from .ha_builder_entities import BuilderSensor, BuilderNumber
from .projector_platform import sensor_entities as projector_sensor_entities

SENSORS = (
    ("devices_total", "Appareils découverts / Discovered devices", None),
    ("device_inventory", "Inventaire équipements / Device inventory", None),
    ("discovery_status", "État découverte / Discovery status", None),
    ("protocol_rx_diagnostics", "Diagnostics réception protocoles / Protocol receive diagnostics", None),
    ("show_network_config", "Configuration réseau Show Network / Show Network network configuration", None),
    ("host_cpu_percent", "CPU hôte HA / HA host CPU", "%"),
    ("host_memory_percent", "RAM hôte HA / HA host memory", "%"),
    ("host_memory_used_bytes", "RAM utilisée / Memory used", "B"),
    ("host_memory_total_bytes", "RAM totale / Total memory", "B"),
    ("performance_level", "Niveau performance / Performance level", None),
    ("performance_interval_s", "Intervalle performance / Performance interval", "s"),
    ("devices_confirmed", "Appareils confirmés / Confirmed devices", None),
    ("devices_candidates", "Candidats / Candidates", None),
    ("ma_packets", "Paquets MA-Net3 / MA-Net3 packets", None),
    ("ma_sources", "Sources MA-Net3 / MA-Net3 sources", None),
    ("ma_groups", "Groupes multicast MA / MA multicast groups", None),
    ("ma_stations", "Stations MA observées / Observed MA stations", None),
    ("ma_live_stations", "Stations MA actives / Live MA stations", None),
    ("ma_sessions", "Sessions MA observées / Observed MA sessions", None),
    ("osc_messages", "Messages OSC / OSC messages", None),
    ("control_mapping_events", "Événements mappings CONTROL / CONTROL mapping events", None),
    ("osc_sent", "OSC envoyés / OSC sent", None),
    ("osc_errors", "Erreurs OSC / OSC errors", None),
    ("timecode_frames", "Timecode frames", None),
    ("ptp_packets", "Paquets PTP / PTP packets", None),
    ("ptp_sources", "Sources PTP / PTP sources", None),
    ("ptp_event_packets", "PTP event packets", None),
    ("ptp_general_packets", "PTP general packets", None),
    ("ptp_last_message_type", "Dernier type PTP / Last PTP message type", None),
    ("dante_packets", "Paquets Dante observés / Dante packets observed", None),
    ("dante_sources", "Sources Dante / Dante sources", None),
    ("dante_mdns_matches", "mDNS correspondant à Dante / Dante mDNS matches", None),
    ("dante_monitor_packets", "Monitoring Dante / Dante monitoring packets", None),
    ("dante_endpoints", "Endpoints Dante observés / Observed Dante endpoints", None),
    ("aes67_sap_packets", "Annonces AES67 SAP / AES67 SAP announcements", None),
    ("aes67_sap_sources", "Sources AES67 SAP / AES67 SAP sources", None),
    ("st2110_rtp_packets", "Paquets RTP ST 2110 / ST 2110 RTP packets", None),
    ("st2110_sources", "Sources ST 2110 / ST 2110 sources", None),
    ("st2110_last_payload_type", "Dernier payload RTP ST 2110 / Last ST 2110 RTP payload", None),
    ("avb_packets", "Paquets AVB / AVB packets", None),
    ("avb_sources", "Sources AVB / AVB sources", None),
    ("audio_protocols_active", "Protocoles audio actifs / Active audio protocols", None),
    ("audio_protocols_stale", "Protocoles audio silencieux / Stale audio protocols", None),
    ("audio_sources", "Sources audio / Audio sources", None),
    ("audio_amplifiers_total", "Amplis audio / Audio amplifiers", None),
    ("audio_amplifiers_online", "Amplis audio en ligne / Online audio amplifiers", None),
    ("audio_amplifiers_errors", "Erreurs amplis audio / Audio amplifier errors", None),
    ("audio_amplifier_temperature_max", "Température max ampli / Max amplifier temperature", "°C"),
    ("dmx_ha_mappings_total", "Mappings DMX → HA / DMX → HA mappings", None),
    ("dmx_ha_zones_total", "Zones DMX → HA / DMX → HA zones", None),
    ("green_go_devices", "Équipements Green-GO / Green-GO devices", None),
    ("green_go_sources", "Sources Green-GO / Green-GO sources", None),
    ("elc_inventory", "Équipements ELC observés / Observed ELC devices", None),
    ("vendor_discovery", "Découvertes fabricants / Vendor discoveries", None),
    ("etc_sensor_catalog", "Capteurs ETC documentés / ETC documented sensors", None),
    ("switch_profiles", "Profils switches disponibles (catalogue) / Available switch profiles (catalogue)", None),
    ("switch_telemetry", "Télémétrie switches / Switch telemetry", None),
    ("projectors_total", "Projecteurs PJLink / PJLink projectors", None),
    ("projectors_online", "Projecteurs PJLink en ligne / Online PJLink projectors", None),
    ("projectors_errors", "Projecteurs PJLink en erreur / PJLink projectors with errors", None),
    ("network_interfaces_up", "Interfaces réseau actives / Network interfaces up", None),
    ("network_interfaces_stale", "Interfaces réseau silencieuses / Stale network interfaces", None),
    ("network_packets_observed", "Paquets réseau observés / Network packets observed", None),
    ("topology_nodes", "Nœuds topologie / Topology nodes", None),
    ("topology_links", "Liens topologie / Topology links", None),
    ("enttec_connected", "ENTTEC DMX USB connecté / ENTTEC DMX USB connected", None),
    ("enttec_frames", "Trames DMX ENTTEC / ENTTEC DMX frames", None),
    ("enttec_valid", "DMX ENTTEC valide / Valid ENTTEC DMX", None),
    ("enttec_error_flags", "Erreurs réception ENTTEC / ENTTEC receive errors", None),
    ("enttec_active_channels", "Canaux DMX ENTTEC actifs / Active ENTTEC DMX channels", None),
    ("enttec_serial_number", "N° série ENTTEC / ENTTEC serial number", None),
    ("security_configured", "Protection Show Network configurée / Security configured", None),
    ("security_unlocked", "Protection Show Network déverrouillée / Security unlocked", None),
    ("security_unlock_remaining_s", "Temps de déverrouillage restant / Security unlock remaining", "s"),
    ("ptp_inter_arrival_ms", "Intervalle PTP / PTP inter-arrival", "ms"),
    ("ptp_jitter_ms", "Jitter PTP / PTP jitter", "ms"),
    ("ptp_clock_present", "Horloge PTP observée / PTP clock observed", None),
    ("ptp_clock_age_s", "Âge horloge PTP / PTP clock age", "s"),
    ("ptp_last_version", "Version PTP observée / Observed PTP version", None),
    ("ptp_dante_v1_observed", "PTPv1 Dante observé / Dante PTPv1 observed", None),
    ("ptp_v2_observed", "PTPv2 observé / PTPv2 observed", None),
    ("aes67_session_count", "Sessions AES67 SDP / AES67 SDP sessions", None),
    ("aes67_fresh_sessions", "Sessions AES67 fraîches / Fresh AES67 sessions", None),
    ("network_capacity_utilization", "Utilisation réseau prédictive / Predicted network utilization", "%"),
    ("network_capacity_link_mbps", "Lien réseau / Network link", "Mbit/s"),
    ("network_capacity_total_mbps", "Débit théorique / Theoretical throughput", "Mbit/s"),
    ("network_capacity_headroom_mbps", "Marge réseau / Network headroom", "Mbit/s"),
    ("chaos_status", "État simulation / Simulation state", None),
    ("journal_archive", "Journal Show Network / Show Network journal", None),
    ("backup_storage", "Stockage sauvegardes / Backup storage", None),
    ("backup_last_success", "Dernière sauvegarde / Last backup", None),
    ("backup_free_bytes", "Espace sauvegarde disponible / Backup free space", "B"),
    ("ha_builder", "Éléments HA Builder / HA Builder items", None),
    ("notification", "Notifications Show Network / Show Network notifications", None),
    ("punchlight_network", "PunchLight réseau / PunchLight network", None),
    ("power_manager_button_count", "Boutons Power Manager / Power Manager buttons", None),
    ("power_manager_active", "Power Manager actifs / Active Power Manager buttons", None),
    ("power_manager_sent", "Trames Power Manager envoyées / Power Manager frames sent", None),
    ("power_manager_errors", "Erreurs Power Manager / Power Manager errors", None),
    ("dmx_circuit_group_count", "Groupes DMX surveillés / Monitored DMX circuit groups", None),
    ("dmx_circuit_groups_alert", "Alertes circuits DMX / DMX circuit alerts", None),
    ("watchdog_active", "Watchdogs en alerte / Active watchdogs", None),
    ("watchdog_rules", "Règles Signal Watchdog / Signal watchdog rules", None),
)


class ShowNetworkSensor(ShowNetworkEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit=None):
        ShowNetworkEntity.__init__(self, coordinator, f"{key}")
        self._key = key
        self._attr_name = name
        # SENSORS entries are (key, name, unit).  Keep the tuple contract
        # explicit so platform setup cannot fail when a unit is present.
        self._declared_unit = unit
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
        if key == "backup_last_success":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        if self._key == "host_cpu_percent":
            return self.coordinator.data.get("host_metrics", {}).get("cpu_percent", 0)
        if self._key == "host_memory_percent":
            return self.coordinator.data.get("host_metrics", {}).get("memory_percent", 0)
        if self._key == "host_memory_used_bytes":
            return self.coordinator.data.get("host_metrics", {}).get("memory_used_bytes", 0)
        if self._key == "host_memory_total_bytes":
            return self.coordinator.data.get("host_metrics", {}).get("memory_total_bytes", 0)
        if self._key == "performance_level":
            return self.coordinator.data.get("performance", {}).get("level", "normal")
        if self._key == "performance_interval_s":
            return self.coordinator.data.get("performance", {}).get("telemetry_interval_s", 5.0)
        if self._key == "show_network_config":
            return "configured"
        if self._key == "ha_builder":
            return len(self.coordinator.data.get("ha_builder", []))
        if self._key == "notification":
            return "active" if self.coordinator.data.get("notification", {}).get("enabled") else "inactive"
        if self._key == "punchlight_network":
            return len(self.coordinator.data.get("punchlight_network", []))
        if self._key == "device_inventory":
            return len(self.coordinator.data.get("device_inventory", []))
        if self._key == "discovery_status":
            status = self.coordinator.data.get("discovery_status", {})
            return status.get("state", "idle")
        if self._key == "network_capacity_utilization":
            return self.coordinator.data.get("network_capacity", {}).get("utilization_pct", 0)
        if self._key == "network_capacity_link_mbps":
            return self.coordinator.data.get("network_capacity", {}).get("link_mbps", 0)
        if self._key == "network_capacity_total_mbps":
            return self.coordinator.data.get("network_capacity", {}).get("total_mbps", 0)
        if self._key == "network_capacity_headroom_mbps":
            return self.coordinator.data.get("network_capacity", {}).get("headroom_mbps", 0)
        if self._key.startswith("network_"):
            return self.coordinator.data.get("network_health", {}).get(self._key.removeprefix("network_"), 0)
        if self._key == "ma_stations":
            return self.coordinator.data.get("ma_remote", {}).get("station_count", 0)
        if self._key == "ma_live_stations":
            return self.coordinator.data.get("ma_remote", {}).get("live_stations", 0)
        if self._key == "ma_sessions":
            return self.coordinator.data.get("ma_remote", {}).get("session_count", 0)
        if self._key == "topology_nodes":
            return len(self.coordinator.data.get("topology", {}).get("nodes", []))
        if self._key == "topology_links":
            return len(self.coordinator.data.get("topology", {}).get("links", []))
        if self._key == "timecode_frames":
            return self.coordinator.data.get("timecode", {}).get("frames", 0)
        if self._key.startswith("security_"):
            return self.coordinator.data.get("security", {}).get(self._key.removeprefix("security_"), False)
        if self._key.startswith("ptp_"):
            return self.coordinator.data.get(self._key, 0)
        if self._key == "dmx_ha_mappings_total":
            return len(self.coordinator.data.get("dmx_ha_mappings", []))
        if self._key == "dmx_ha_zones_total":
            return len(self.coordinator.data.get("dmx_ha_zones", []))
        if self._key == "chaos_status":
            return "active" if self.coordinator.data.get("chaos", {}).get("active") else "inactive"
        if self._key == "journal_archive":
            return self.coordinator.data.get("archive", {}).get("files", 0)
        if self._key == "backup_storage":
            return "ready" if self.coordinator.data.get("archive", {}).get("storage_ready", False) else "not_ready"
        if self._key == "backup_last_success":
            value = self.coordinator.data.get("archive", {}).get("last_backup_success")
            try:
                return datetime.fromisoformat(value) if value else None
            except (TypeError, ValueError):
                return None
        if self._key == "backup_free_bytes":
            return self.coordinator.data.get("archive", {}).get("storage_free_bytes")
        value = self.coordinator.data.get(self._key, 0)
        if self._key in ("audio_protocols_active", "audio_protocols_stale"):
            return len(value or [])
        if self._key == "audio_sources":
            return sum((value or {}).values())
        # HA entity states must be scalar and <=255 characters. Collections
        # are represented by their item count; the full payload belongs in
        # attributes below. This prevents catalog/inventory sensors becoming
        # unknown because Home Assistant rejects oversized list/dict states.
        if isinstance(value, (list, tuple, set, dict)):
            return len(value)
        return value

    @property
    def extra_state_attributes(self):
        if self._key == "show_network_config":
            return dict(self.coordinator.data.get("show_network_config", {}))
        if self._key == "ha_builder":
            return {"items": self.coordinator.data.get("ha_builder", [])}
        if self._key == "notification":
            return {"enabled": self.coordinator.data.get("notification", {}).get("enabled", False), "target_configured": bool(self.coordinator.data.get("notification", {}).get("target"))}
        if self._key == "punchlight_network":
            return {"devices": self.coordinator.data.get("punchlight_network", [])}
        if self._key.startswith("power_manager_"):
            return {"buttons": self.coordinator.data.get("power_manager_buttons", []), "outputs": self.coordinator.data.get("power_manager_outputs", []), "last_error": self.coordinator.data.get("power_manager_last_error")}
        if self._key.startswith("dmx_circuit_"):
            return {"groups": self.coordinator.data.get("dmx_circuit_groups", [])}
        if self._key in {"watchdog_active", "watchdog_rules"}:
            return {"rules": self.coordinator.data.get("watchdog_rules", [])}
        if self._key == "osc_messages":
            return {"osc_input": dict(self.coordinator.data.get("osc_input", {})), "osc_learn": dict(self.coordinator.data.get("osc_learn", {}))}
        if self._key == "control_mapping_events":
            from dataclasses import asdict, is_dataclass
            mappings=[]
            for item in self.coordinator.control_mapping_engine.mappings.values():
                mappings.append(asdict(item) if is_dataclass(item) else dict(item))
            return {"mappings": mappings, "events": list(self.coordinator.data.get("control_mapping_events", []))}
        if self._key == "dmx_ha_zones_total":
            from .hue_catalog import snapshot as hue_catalog_snapshot
            return {"zones": self.coordinator.data.get("dmx_ha_zones", []), "rdm": self.coordinator.data.get("dmx_ha_rdm", {}), "hue_catalog": hue_catalog_snapshot()}
        if self._key == "dmx_ha_mappings_total":
            return {"mappings": self.coordinator.data.get("dmx_ha_mappings", [])}
        if self._key in {"topology_nodes", "topology_links"}:
            return {"topology": self.coordinator.data.get("topology", {"nodes": [], "links": []})}
        if self._key == "journal_archive":
            return dict(self.coordinator.data.get("archive", {}))
        if self._key == "discovery_status":
            return dict(self.coordinator.data.get("discovery_status", {}))
        if self._key == "protocol_rx_diagnostics":
            return dict(self.coordinator.data.get("protocol_rx_diagnostics", {}))
        if self._key in {"projectors_total", "projectors_online", "projectors_errors"}:
            return dict(self.coordinator.data.get("projector_status", {}))
        if self._key in {"ma_packets", "ma_sources", "ma_groups", "ma_stations", "ma_live_stations", "ma_sessions"}:
            return {"ma_remote": self.coordinator.data.get("ma_remote", {}), "rx_diagnostics": self.coordinator.data.get("protocol_rx_diagnostics", {}).get("ma_net3", {})}
        if self._key == "device_inventory":
            rows = self.coordinator.data.get("device_inventory", [])
            # Compact presentation data only; raw evidence stays available in the inventory panel.
            return {"devices": [{k: row.get(k) for k in (
                "unique_id", "display_name", "display_manufacturer", "display_model",
                "custom_role", "custom_location", "hidden", "monitor_mode", "ip", "ipv6", "hostname",
                "mac", "serial", "category", "protocols", "sources", "confidence"
            )} for row in rows]}
        if self._key == "etc_sensor_catalog":
            return {"sensors": self.coordinator.data.get("etc_sensor_catalog", [])}
        if self._key == "vendor_discovery":
            return {"services": self.coordinator.data.get("vendor_discovery", [])}
        if self._key == "switch_profiles":
            return {"profiles": self.coordinator.data.get("switch_profiles", [])}
        if self._key == "switch_telemetry":
            return {"switches": self.coordinator.data.get("switch_telemetry", [])}
        if self._key in {"audio_amplifiers_total", "audio_amplifiers_online", "audio_amplifiers_errors", "audio_amplifier_temperature_max"}:
            return {"amplifiers": self.coordinator.data.get("audio_amplifiers", []), "stale_timeout_s": self.coordinator.data.get("audio_amplifier_stale_timeout_s")}
        if self._key in {"aes67_sap_packets", "aes67_sap_sources", "aes67_session_count", "aes67_fresh_sessions"}:
            return {"sessions": self.coordinator.data.get("aes67_sessions", []), "last_seen": self.coordinator.data.get("aes67_last_seen"), "sap_group": self.coordinator.data.get("aes67_sap_group"), "sap_port": self.coordinator.data.get("aes67_sap_port")}
        if self._key in {"ptp_clock_present", "ptp_clock_age_s", "ptp_last_version", "ptp_dante_v1_observed", "ptp_v2_observed"}:
            return {k:v for k,v in self.coordinator.data.items() if k.startswith("ptp_")}
        if self._key == "elc_inventory":
            return {"devices": self.coordinator.data.get("elc_inventory", [])}
        if self._key in {"backup_storage", "backup_last_success", "backup_free_bytes"}:
            archive = self.coordinator.data.get("archive", {})
            return {
                "mounted": archive.get("storage_mounted", False),
                "requires_mount": archive.get("storage_requires_mount", False),
                "writable": archive.get("storage_writable", False),
                "destination": archive.get("destination"),
                "last_backup_error": archive.get("last_backup_error"),
                "last_backup_path": archive.get("last_backup_path"),
                "retention_days": archive.get("retention_days"),
            }
        return None

    @property
    def native_unit_of_measurement(self):
        if self._declared_unit is not None:
            return self._declared_unit
        if self._key in {"network_capacity_utilization"}: return "%"
        if self._key in {"network_capacity_link_mbps", "network_capacity_total_mbps", "network_capacity_headroom_mbps"}: return "Mbit/s"
        if self._key in {"audio_amplifier_temperature_max"}: return "°C"
        if self._key in {"security_unlock_remaining_s"}: return "s"
        if self._key in {"ptp_inter_arrival_ms", "ptp_jitter_ms"}: return "ms"
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ShowNetworkCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [ShowNetworkSensor(coordinator, *item) for item in SENSORS]
    hosts = getattr(coordinator.gigacore, "hosts", []) if coordinator.gigacore else []
    entities.extend(GigaCoreTemperatureSensor(coordinator, f"gigacore_temperature_{i}", host, i) for i, host in enumerate(hosts))
    entities.append(DmxUniverseSensor(coordinator))
    entities.append(TimecodeSensor(coordinator))
    entities.extend(projector_sensor_entities(coordinator))
    entities.extend(BuilderSensor(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "sensor" and item.enabled)
    entities.extend(BuilderNumber(coordinator, item) for item in coordinator.ha_builder.items.values() if item.entity_type == "number" and item.enabled)
    async_add_entities(entities)
    coordinator.ha_builder_callbacks = getattr(coordinator, "ha_builder_callbacks", {})
    coordinator.ha_builder_callbacks["sensor"] = lambda item: async_add_entities([BuilderSensor(coordinator, item)])
    coordinator.ha_builder_callbacks["number"] = lambda item: async_add_entities([BuilderNumber(coordinator, item)])
    coordinator.ha_builder_remove_callbacks = getattr(coordinator, "ha_builder_remove_callbacks", {})



class DmxUniverseSensor(ShowNetworkEntity, SensorEntity):
    """Live DMX universe summary for the frontend and diagnostics."""

    _attr_name = "DMX Universes / Univers DMX"

    def __init__(self, coordinator):
        ShowNetworkEntity.__init__(self, coordinator, "dmx_universes")

    @property
    def native_value(self):
        return len(self.coordinator.data.get("dmx_universes", []))

    @property
    def extra_state_attributes(self):
        # Keep HA state small: raw 512-byte frames are packed as base64 instead
        # of a 512-item JSON integer array. The live DMX panel decodes it.
        compact = []
        for item in self.coordinator.data.get("dmx_universes", []):
            row = {k: item.get(k) for k in (
                "protocol", "universe", "source", "priority", "sequence",
                "packet_rate", "active_channels", "last_change", "interface",
                "inter_arrival_ms", "jitter_ms", "sequence_loss_pct"
            )}
            # Coordinator already publishes the live 512-byte frame as base64.
            # Do not re-encode from the removed ``values`` list: doing so turned
            # every valid live frame into an empty payload in HA attributes.
            packed = item.get("values_b64")
            if isinstance(packed, str) and packed:
                row["values_b64"] = packed
            else:
                values = item.get("values") or []
                try:
                    row["values_b64"] = base64.b64encode(bytes(values[:512])).decode("ascii")
                except (TypeError, ValueError):
                    row["values_b64"] = ""
            compact.append(row)
        return {
            "universes": compact,
            "network_health": self.coordinator.data.get("dmx_network_health", {}),
            "configured_universes": self.coordinator.data.get("show_network_config", {}).get("universes", ""),
            "configured_interface": self.coordinator.data.get("show_network_config", {}).get("interface_dmx"),
            "artnet_enabled": self.coordinator.data.get("show_network_config", {}).get("dmx_artnet_enabled"),
            "sacn_enabled": self.coordinator.data.get("show_network_config", {}).get("dmx_sacn_enabled"),
            "source_filter": self.coordinator.data.get("show_network_config", {}).get("dmx_source", ""),
        }


# Temperature entities are dynamically created later when a GigaCore is confirmed.
class GigaCoreTemperatureSensor(ShowNetworkEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, unique_id, label, index=None):
        ShowNetworkEntity.__init__(self, coordinator, unique_id)
        self._label = label
        self._index = index
        self._attr_name = f"GigaCore {label} - Température / Temperature"

    @property
    def native_value(self):
        return self.coordinator.data.get("giga_core_temperature", {}).get(self._label)


class TimecodeSensor(ShowNetworkEntity, SensorEntity):
    """Latest passive Art-Net TimeCode value."""
    _attr_name = "Timecode"
    _attr_icon = "mdi:timer-outline"
    def __init__(self, coordinator):
        ShowNetworkEntity.__init__(self, coordinator, "timecode")
    @property
    def native_value(self):
        return self.coordinator.data.get("timecode", {}).get("text", "--:--:--:--")
    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("timecode", {})
