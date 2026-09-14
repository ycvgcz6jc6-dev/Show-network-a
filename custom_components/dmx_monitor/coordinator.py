"""Home Assistant coordinator for Show Network telemetry."""
from __future__ import annotations

import asyncio
import base64

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .device_inventory import DeviceInventory
from .green_go import GreenGOInventory
from .elc import ELCInventory
from .gigacore import GigaCoreMonitor
from .etc import profile as etc_profile
from .switch_profiles import enabled_profiles
from .lighting_receiver import UniverseTracker
from .signal_watchdog import SignalWatchdogManager
from .rules import RuleSet
from .security import SecurityManager
from .network_interfaces import snapshot as network_interface_snapshot
from .topology import ShowTopology
from .rule_storage import RuleStore
from .projector_monitor import PJLinkMonitor
from .network_health import NetworkHealth
from .ma_remote import MARemoteInventory
from .audio_amplifiers import AudioAmplifierInventory
from .dmx_ha_mapping import DmxHAMappingEngine
from .dmx_ha_mapping_storage import DmxHAMappingStore
from .dmx_ha_zones import DmxHAZoneEngine, DmxHAZone
from .backup import ConfigBackupManager
from .osc_output import OSCOutput, OSCTargetStore
from .timecode import TimecodeMonitor
from .reliability import ChaosSimulator, capacity_snapshot
from .rate_limiter import RateLimiter
from .flow_pipeline import LatestValuePipeline
from .ha.action_dispatcher import HAActionDispatcher
from .core.contracts import ServiceAction
from .core.state_store import RuntimeStateStore
from .host_metrics import snapshot as host_metrics_snapshot
from .performance_manager import AdaptivePerformance
from .osc_learn import OSCLearnSession

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=5)


class ShowNetworkCoordinator(DataUpdateCoordinator[dict]):
    """Central coordinator for passive inspectors and read-only pollers."""

    def __init__(self, hass: HomeAssistant, inventory: DeviceInventory, gigacore: GigaCoreMonitor | None = None) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="show_network",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.inventory = inventory
        self.green_go = GreenGOInventory()
        self.elc = ELCInventory()
        self.vendor_discovery = []
        self.gigacore = gigacore
        self.ma_listener = None
        self.ma_remote = MARemoteInventory()
        self.ptp_monitor = None
        self.dante_monitor = None
        self.aes67_monitor = None
        self.st2110_monitor = None
        self.avb_monitor = None
        self.enttec_input = None
        self.punchlight = None
        self.resource_registry = None
        self.performance_manager = AdaptivePerformance("auto")
        self.enttec_listen_enabled = bool(self.enttec_input)
        self.dmx_tracker = UniverseTracker()
        self._dmx_universe_entity_keys: set[tuple[str, int]] = set()
        self.dmx_universe_entity_callback = None
        self.watchdogs = SignalWatchdogManager(hass, action_guard=self._watchdog_action_allowed, event_callback=self._watchdog_event)
        self.rules = RuleSet()
        self.rule_store = RuleStore(hass.config.path())
        for _rule in self.rule_store.load():
            try:
                self.rules.add(_rule)
            except (ValueError, TypeError):
                _LOGGER.warning("Ignoring invalid persisted Show Network rule: %s", getattr(_rule, "name", "?"))
        self.topology = ShowTopology()
        self.network_health = NetworkHealth()
        self.audio_amplifiers = AudioAmplifierInventory()
        self.archive = None
        self.chaos = ChaosSimulator()
        self.capacity_config = {"link_mbps": 1000.0, "dante_mbps": 0.0, "cameras_mbps": 0.0, "st2110_mbps": 0.0, "other_mbps": 0.0}
        self._timeline_dmx_hashes = {}
        self._dmx_publish_limiter = RateLimiter(interval_s=0.05)
        # Node-RED-inspired latest-value pipeline: watchdogs see every packet,
        # while rules/HA mappings process coalesced snapshots at a bounded rate.
        self._dmx_flow = LatestValuePipeline(self._process_dmx_snapshot, interval_s=0.05, max_keys=256, byte_change_threshold=1)
        self._ha_dispatcher = HAActionDispatcher(hass)
        self.state_store = RuntimeStateStore(history_limit=100)
        # Safety gate: light/scene actions remain blocked until explicitly enabled.
        self.light_sync_enabled = False
        from .osc_mapping import Mapping, MappingEngine
        self.control_mapping_engine = MappingEngine()
        from .control_mapping import ControlMappingStore
        self.control_mapping_store = ControlMappingStore(hass.config.path("show_network_control_mappings.json"))
        from dataclasses import fields
        for _raw in self.control_mapping_store.load():
            try:
                allowed = {f.name for f in fields(Mapping)}
                self.control_mapping_engine.add(Mapping(**{k: v for k, v in _raw.items() if k in allowed}))
            except (TypeError, ValueError, KeyError):
                _LOGGER.warning("Ignoring invalid persisted control mapping")
        self.dmx_ha_mapping_engine = DmxHAMappingEngine()
        self._dmx_ha_highlights: dict[str, dict[str, dict]] = {}
        self.dmx_ha_mapping_store = DmxHAMappingStore(hass.config.path())
        self.dmx_ha_zone_engine = DmxHAZoneEngine()
        self.dmx_ha_zone_store_path = hass.config.path("show_network_dmx_ha_zones.json")
        self._load_dmx_ha_zones()
        self.config_backups = ConfigBackupManager(hass.config.path())
        for _mapping in self.dmx_ha_mapping_store.load():
            self.dmx_ha_mapping_engine.add(_mapping)
        self.control_mapping_events = []
        self.osc_output = OSCOutput()
        self.osc_learn = OSCLearnSession()
        self.osc_target_store = OSCTargetStore(hass.config.path("show_network_osc_targets.json"))
        self.osc_targets = {x.target_id: x for x in self.osc_target_store.load()}
        self.timecode = TimecodeMonitor()
        self.projector_monitor = PJLinkMonitor()
        self.security = SecurityManager(hass.config.path(), autoload=False)
        self._last_activity = {}
        self.data = {
            "devices_total": 0,
            "devices_confirmed": 0,
            "devices_candidates": 0,
            "devices_unknown": 0,
            "device_inventory": [],
            "discovery_status": {"state": "idle", "mdns_state": "idle", "mdns_services": 0, "mdns_detail": "not scanned yet", "arp_neighbors": 0, "inventory_total": 0, "errors": []},
            "protocol_rx_diagnostics": {},
            "device_overrides": {},
            "ma_packets": 0,
            "ma_sources": 0,
            "ma_groups": 0,
            "osc_messages": 0,
            "osc_output_enabled": False,
            "osc_sent": 0,
            "osc_errors": 0,
            "osc_last_target": None,
            "osc_last_address": None,
            "osc_last_error": None,
            "timecode": self.timecode.snapshot(),
            "giga_core_temperature": {},
            "gigacore_status": {},
            "control_mappings": list(self.control_mapping_engine.mappings),
            "control_mapping_events": [],
            "osc_input": {"enabled": False, "messages": 0, "last_address": None, "last_source": None, "last_error": None},
            "osc_learn": {"active": False, "suggestions": []},
            "midi_input": {"enabled": False, "connected": False, "messages": 0, "port": None, "last_error": None},
            "ptp_packets": 0,
            "ptp_sources": 0,
            "ptp_event_packets": 0,
            "ptp_general_packets": 0,
            "ptp_last_source": None,
            "ptp_last_message_type": None,
            "ptp_last_version": None,
            "ptp_last_domain": None,
            "ptp_last_length": None,
            "dante_packets": 0,
            "dante_sources": 0,
            "dante_mdns_packets": 0,
            "dante_mdns_matches": 0,
            "dante_monitor_packets": 0,
            "dante_setup_packets": 0,
            "dante_last_source": None,
            "dante_last_kind": None,
            "dante_last_port": None,
            "dante_last_length": None,
            "dante_endpoints": 0,
            "dante_inventory": [],
            "aes67_sap_packets": 0,
            "aes67_sap_sources": 0,
            "aes67_last_source": None,
            "aes67_last_length": None,
            "aes67_last_hint": None,
            "st2110_packets": 0,
            "st2110_rtp_packets": 0,
            "st2110_sources": 0,
            "st2110_last_source": None,
            "st2110_last_payload_type": None,
            "st2110_last_sequence": None,
            "st2110_last_timestamp": None,
            "st2110_last_size": None,
            "green_go_devices": 0,
            "green_go_sources": 0,
            "etc_sensor_catalog": [],
            "switch_profiles": [],
            "switch_manufacturers": [],
            "enttec_connected": False,
            "enttec_frames": 0,
            "enttec_valid": False,
            "enttec_error_flags": 0,
            "enttec_active_channels": 0,
            "enttec_serial_number": None,
            "enttec_device": None,
            "enttec_model": None,
            "enttec_values": bytes(512),
            "punchlight": {"configured": False, "connected": False, "recording": False, "ready": False, "messages": 0},
            "dmx_universes": [],
            "watchdog_rules": [],
            "watchdog_active": 0,
            "dmx_rules": [],
            "dmx_rule_traces": [],
            "topology": {"nodes": [], "links": []},
            "network_health": {"interfaces": [], "interfaces_up": 0, "interfaces_stale": 0, "packets_observed": 0, "protocols": []},
            "light_sync_enabled": False,
            "dmx_ha_mappings": self.dmx_ha_mapping_engine.snapshot(),
            "dmx_ha_zones": self.dmx_ha_zone_engine.snapshot(),
            "dmx_ha_rdm": self.dmx_ha_zone_engine.rdm_snapshot(),
            "projector_control_enabled": False,
            "security": self.security.snapshot(),
            "network_interfaces": [],
            "chaos": self.chaos.snapshot(),
            "network_capacity": capacity_snapshot([], **self.capacity_config),
            "archive": {},
            "runtime_resources": [],
            "host_metrics": host_metrics_snapshot().snapshot(),
            "performance": {"profile": "auto", "level": "normal", "telemetry_interval_s": 5.0, "discovery_enabled": True, "secondary_polling": True},
        }


    async def async_set_dmx_ha_mapping_highlight(self, mapping_id: str, enabled: bool) -> None:
        """Temporarily highlight mapped HA lights, restoring their exact prior state."""
        mapping = self.dmx_ha_mapping_engine.mappings.get(mapping_id)
        if not mapping or not mapping.entity_id:
            raise ValueError("Mapping inconnue ou sans entité Home Assistant")
        entity_ids = mapping.entity_id if isinstance(mapping.entity_id, list) else [mapping.entity_id]
        saved = self._dmx_ha_highlights.get(mapping_id, {})
        if enabled:
            for entity_id in entity_ids:
                if entity_id in saved:
                    continue
                state = self.hass.states.get(entity_id)
                if not state:
                    continue
                saved[entity_id] = {"state": state.state, "attributes": dict(state.attributes)}
                data = {"entity_id": entity_id, "brightness_pct": 100}
                modes = state.attributes.get("supported_color_modes") or []
                if any(mode in modes for mode in ("rgb", "rgbw", "rgbw_color", "hs", "xy")):
                    data["rgb_color"] = [255, 255, 255]
                await self.hass.services.async_call("light", "turn_on", data, blocking=True)
            self._dmx_ha_highlights[mapping_id] = saved
        else:
            for entity_id, previous in saved.items():
                if previous.get("state") == "off":
                    await self.hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
                    continue
                attrs = previous.get("attributes", {})
                data = {"entity_id": entity_id}
                if "brightness" in attrs:
                    data["brightness"] = attrs["brightness"]
                if "rgb_color" in attrs:
                    data["rgb_color"] = attrs["rgb_color"]
                elif "color_temp_kelvin" in attrs:
                    data["color_temp_kelvin"] = attrs["color_temp_kelvin"]
                elif "color_temp" in attrs:
                    data["color_temp"] = attrs["color_temp"]
                if "effect" in attrs and attrs["effect"] is not None:
                    data["effect"] = attrs["effect"]
                await self.hass.services.async_call("light", "turn_on", data, blocking=True)
            self._dmx_ha_highlights.pop(mapping_id, None)

    async def set_enttec_listen_enabled(self, enabled: bool) -> None:
        """Enable/disable receive-only ENTTEC USB listening without DMX output."""
        enttec = getattr(self, "enttec_input", None)
        if enabled:
            if enttec is None:
                raise RuntimeError("Aucun périphérique ENTTEC configuré")
            await enttec.start() if not enttec.connected else asyncio.sleep(0)
        else:
            if enttec is not None and enttec.connected:
                await enttec.stop()
        self.enttec_listen_enabled = bool(enabled)
        self.publish(enttec_listen_enabled=self.enttec_listen_enabled)

    async def _async_update_data(self) -> dict:
        """Return a snapshot from the currently active inspectors.

        Protocol workers should update the snapshot and call
        async_set_updated_data() for push-style telemetry. The periodic refresh
        keeps the entity layer alive and allows future read-only pollers.
        """
        summary = self.inventory.summary()
        if self.gigacore:
            await self.gigacore.async_update()
        if getattr(self, "projector_monitor_enabled", True):
            await self.projector_monitor.async_update()
        snapshot = dict(self.data)
        snapshot["security"] = self.security.snapshot()
        snapshot["network_interfaces"] = await self.hass.async_add_executor_job(network_interface_snapshot)
        host = host_metrics_snapshot()
        snapshot["host_metrics"] = host.snapshot()
        decision = self.performance_manager.decide(host.cpu_percent, host.memory_percent)
        snapshot["performance"] = {"profile": self.performance_manager.profile, "level": decision.level, "telemetry_interval_s": decision.telemetry_interval_s, "discovery_enabled": decision.discovery_enabled, "secondary_polling": decision.secondary_polling}
        # Adapt only the coordinator refresh cadence; protocol listeners/watchdogs remain independent.
        self.update_interval = timedelta(seconds=decision.telemetry_interval_s)
        if self.resource_registry is not None:
            snapshot["runtime_resources"] = self.resource_registry.snapshot()
        snapshot.update(
            devices_total=summary["total"],
            devices_confirmed=summary["confirmed"],
            devices_candidates=summary["candidates"],
        )
        snapshot["giga_core_temperature"] = dict(self.gigacore.temperatures) if self.gigacore else {}
        snapshot["gigacore_status"] = self.gigacore.snapshot() if self.gigacore else {}
        gg = self.green_go.snapshot()
        snapshot["green_go_devices"] = len(gg)
        snapshot["green_go_sources"] = len({d.get("source") for d in gg if d.get("source")})
        snapshot["green_go_inventory"] = gg
        snapshot["elc_inventory"] = self.elc.snapshot()
        snapshot["vendor_discovery"] = list(self.vendor_discovery)
        snapshot["etc_sensor_catalog"] = etc_profile().get("sensors", [])
        snapshot["switch_profiles"] = [p.key for p in enabled_profiles(self.data.get("switch_manufacturers"))]
        self.topology.ingest_inventory(self.inventory.public())
        # Promote every observed DMX/audio/control source into the topology with
        # evidence, while keeping the topology descriptive/read-only.
        for item in self.dmx_tracker.all():
            node_id = f"ip:{item.source}" if item.source else f"source:{item.protocol}:{item.universe}"
            self.topology.observe_protocol(node_id, item.protocol, label=item.source or node_id,
                                           ip=item.source if item.source else None,
                                           category="show_network_source", confidence=0.8,
                                           source="dmx_observation")
            if item.source:
                self.inventory.upsert(
                    ip=item.source, protocols={item.protocol}, sources={"dmx_passive"},
                    confidence="candidate", confidence_score=0.8, unique_id=f"candidate:{item.source}",
                    evidence=[{"field":"universe","value":item.universe,"source":"dmx_passive","confidence":0.9}],
                )
            self.network_health.observe_packet(item.interface or "unknown", item.protocol)
        # MA-Net3 station sources are also genuine passive discovery evidence.
        for station in self.ma_remote.snapshot().get("stations", []):
            ip = station.get("ip")
            if ip:
                self.inventory.upsert(ip=ip, protocols={"MA-Net3"}, sources={"ma_net3_passive"},
                                      confidence="candidate", confidence_score=0.8, unique_id=f"candidate:{ip}")
        snapshot["device_inventory"] = self.inventory.public(include_hidden=True)
        snapshot["device_overrides"] = dict(self.inventory.overrides)
        snapshot["topology"] = self.topology.snapshot()
        snapshot["network_health"] = self.network_health.snapshot()
        if self.ptp_monitor:
            snapshot.update(self.ptp_monitor.snapshot())
        if self.dante_monitor:
            snapshot.update(self.dante_monitor.snapshot())
        if self.aes67_monitor:
            snapshot.update(self.aes67_monitor.snapshot())
        if getattr(self, "aes70_monitor", None):
            snapshot.update(self.aes70_monitor.snapshot())
        if self.st2110_monitor:
            snapshot.update(self.st2110_monitor.snapshot())
        if self.avb_monitor:
            snapshot.update({f"avb_{k}": v for k, v in self.avb_monitor.snapshot().items()})
        if getattr(self, "audio_health", None):
            snapshot.update(self.audio_health.snapshot(
                dante=self.dante_monitor.snapshot() if self.dante_monitor else None,
                ptp=self.ptp_monitor.snapshot() if self.ptp_monitor else None,
                aes67=self.aes67_monitor.snapshot() if self.aes67_monitor else None,
                st2110=self.st2110_monitor.snapshot() if self.st2110_monitor else None,
                avb=self.avb_monitor.snapshot() if self.avb_monitor else None,
            ))
        # Passive manufacturer-aware amplifier inventory. No vendor commands are sent.
        if self.dante_monitor:
            for row in self.dante_monitor.snapshot().get("dante_inventory", []):
                text = " ".join(row.get("markers", []) + row.get("services", [])).lower()
                # Conservative candidates: manufacturer evidence must come from observed payload markers.
                hints = (("l_acoustics", "l-acoustics"), ("d_and_b", "d&b"), ("d_and_b", "db audiotechnik"), ("lab_gruppen_lake", "lab gruppen"), ("adamson", "adamson"))
                for manufacturer, marker in hints:
                    if marker in text:
                        self.audio_amplifiers.observe(key=f"{manufacturer}:{row.get("source")}", manufacturer=manufacturer, host=row.get("source"), protocol="Dante/mDNS", evidence=marker)
        snapshot.update(self.audio_amplifiers.snapshot())
        if self.enttec_input:
            snapshot.update(self.enttec_input.snapshot())
        if self.punchlight:
            snapshot["punchlight"] = self.punchlight.snapshot()
        snapshot["projectors"] = self.projector_monitor.snapshot()
        snapshot["network_capacity"] = capacity_snapshot(snapshot.get("dmx_universes", []), **self.capacity_config)
        snapshot["chaos"] = self.chaos.snapshot()
        snapshot["archive"] = await self.hass.async_add_executor_job(self.archive.status) if self.archive else {}
        if getattr(self, "dmx_network", None):
            snapshot["dmx_network_health"] = self.dmx_network.snapshot()
        else:
            snapshot["dmx_network_health"] = {}
        snapshot["dmx_universes"] = [
            {
                "protocol": item.protocol,
                "universe": item.universe,
                "source": item.source,
                "priority": item.priority,
                "sequence": item.sequence,
                "packet_rate": round(item.packet_rate, 2),
                "active_channels": item.active_channels,
                "last_change": item.last_change,
                "interface": item.interface,
                "inter_arrival_ms": item.inter_arrival_ms,
                "jitter_ms": item.jitter_ms,
                "sequence_loss_pct": item.sequence_loss_pct,
                "values_b64": base64.b64encode(item.values).decode("ascii"),
            }
            for item in self.dmx_tracker.all()
        ]
        snapshot.update(self.watchdogs.snapshot())
        snapshot["network_capacity"] = capacity_snapshot(snapshot.get("dmx_universes", []), **self.capacity_config)
        if self.archive:
            self._archive_transitions(snapshot)
        rx_diag = {"dmx": self.dmx_network.snapshot() if self.dmx_network else {"running": False, "error": "receiver unavailable"}}
        if self.ma_listener:
            ma = self.ma_listener.snapshot()
            snapshot.update(ma_packets=ma["packets"], ma_sources=ma["sources"], ma_groups=ma["groups"])
            rx_diag["ma_net3"] = ma.get("diagnostics", {})
            for obs in ma.get("observations", [])[-50:]:
                try:
                    self.ma_remote.observe(obs.source_ip, obs.destination_group)
                except AttributeError:
                    self.ma_remote.observe(obs["source_ip"], obs["destination_group"])
            snapshot["ma_remote"] = self.ma_remote.snapshot()
        else:
            rx_diag["ma_net3"] = {"state": "disabled_or_unavailable", "interface": snapshot.get("show_network_config", {}).get("interface_ma")}
        rx_diag["mdns"] = dict(snapshot.get("discovery_status", {}))
        snapshot["protocol_rx_diagnostics"] = rx_diag
        self.data = snapshot
        return snapshot

    def _archive_transitions(self, snapshot: dict) -> None:
        """Record compact protocol state transitions, not raw packet payloads."""
        watched = {
            "ma_sources": "ma", "ptp_sources": "ptp", "dante_sources": "dante",
            "aes67_sap_sources": "aes67", "st2110_sources": "st2110", "avb_sources": "avb",
        }
        for key, kind in watched.items():
            value = snapshot.get(key)
            if value is None:
                continue
            previous = self._last_activity.get(key)
            if previous != value:
                event = "activity_change"
                self.archive.record(kind, event, {"metric": key, "value": value, "previous": previous})
                self._last_activity[key] = value

    def observe_dmx(self, protocol: str, universe: int, source: str, values: bytes, priority=None, sequence=None, interface=None) -> None:
        """Register a DMX frame without propagating every packet to HA entities."""
        key = (str(protocol), int(universe), str(source or ""))
        entity_key = (str(protocol), int(universe))
        if entity_key not in self._dmx_universe_entity_keys:
            self._dmx_universe_entity_keys.add(entity_key)
            if self.dmx_universe_entity_callback:
                try:
                    self.dmx_universe_entity_callback(protocol, int(universe))
                except Exception:
                    _LOGGER.exception("Unable to add dynamic DMX universe entity")
        self.dmx_tracker.observe(protocol, universe, source, values, priority, sequence, interface)
        if self.archive:
            timeline_key = (str(protocol).lower(), int(universe), str(source or ""))
            compact_hash = hash(bytes(values[:512]))
            if self._timeline_dmx_hashes.get(timeline_key) != compact_hash:
                self.archive.record("dmx", "universe_change", {
                    "protocol": protocol, "universe": universe, "source": source,
                    "interface": interface, "active_channels": sum(1 for v in values[:512] if v),
                    "sequence": sequence, "priority": priority,
                })
                self._timeline_dmx_hashes[timeline_key] = compact_hash
        self.watchdogs.observe(protocol, universe, source)
        # Rules and HA mappings use the bounded pipeline; reception and watchdog
        # observation remain synchronous and cheap. HA state publication is also
        # coalesced to <=20 Hz to protect the event bus.
        self._dmx_flow.push_nowait(key, bytes(values[:512]))
        self._dmx_publish_limiter.push_nowait(key, self._publish_dmx_snapshot)

    async def _process_dmx_snapshot(self, key, values: bytes) -> None:
        protocol, universe, source = key
        if self.light_sync_enabled:
            for proposal in self.dmx_ha_mapping_engine.process(universe, source, values):
                self._execute_ha_mapping(proposal)
            for proposal in self.dmx_ha_zone_engine.process(universe, source, values):
                self._execute_ha_mapping(proposal)
        for result in self.rules.evaluate_snapshot(protocol, universe, source, values):
            if result.action_due:
                action = result.action_due
                if self.archive:
                    self.archive.record("system", "rule_action_requested", {"rule": result.rule_name, "domain": action.domain, "service": action.service, "entity_id": action.entity_id})
                self._execute_rule_action(action)

    def async_start_workers(self) -> None:
        """Start bounded background workers once setup is complete."""
        self._ha_dispatcher.start()

    async def _publish_dmx_snapshot(self, _value=None) -> None:
        self.data["dmx_rules"] = self.rules.snapshot()
        self.data["dmx_rule_traces"] = self.rules.trace_snapshot()
        self.data["light_sync_enabled"] = self.light_sync_enabled
        self.data["dmx_universes"] = [
            {
                "protocol": item.protocol, "universe": item.universe, "source": item.source,
                "priority": item.priority, "sequence": item.sequence,
                "packet_rate": round(item.packet_rate, 2), "active_channels": item.active_channels,
                "last_change": item.last_change, "interface": item.interface,
                "inter_arrival_ms": item.inter_arrival_ms,
                "jitter_ms": item.jitter_ms,
                "sequence_loss_pct": item.sequence_loss_pct,
                "values_b64": base64.b64encode(item.values).decode("ascii"),
            } for item in self.dmx_tracker.all()
        ]
        self.data["dmx_publish_rate"] = self._dmx_publish_limiter.snapshot()
        self.data["dmx_flow_pipeline"] = self._dmx_flow.snapshot()
        self.data["ha_action_dispatcher"] = self._ha_dispatcher.snapshot()
        if getattr(self, "dmx_network", None):
            self.data["dmx_network_health"] = self.dmx_network.snapshot()
        self.async_set_updated_data(self.data)


    async def async_stop(self) -> None:
        """Stop coordinator-owned background workers cleanly."""
        await self._dmx_publish_limiter.async_stop()
        await self._dmx_flow.async_stop()
        await self._ha_dispatcher.async_stop()

    def process_control_input(self, address: str, value) -> None:
        """Run unified OSC/MIDI mappings and enqueue accepted HA service calls."""
        for result in self.control_mapping_engine.process(address, value):
            self.control_mapping_events.append({"mapping_id": result.mapping_id, "accepted": result.accepted, "reason": result.reason, "value": result.value, "timestamp": result.timestamp})
            if len(self.control_mapping_events) > 100:
                del self.control_mapping_events[:-100]
            if not result.accepted:
                continue
            mapping = self.control_mapping_engine.mappings.get(result.mapping_id)
            if not mapping:
                continue
            if "." not in mapping.destination:
                _LOGGER.warning("Invalid control mapping destination: %s", mapping.destination)
                continue
            domain, service = mapping.destination.split(".", 1)
            data = {"entity_id": mapping.target}
            data[mapping.attribute or "value"] = result.value
            if not self._ha_dispatcher.submit(ServiceAction(domain, service, data, "control_mapping")):
                _LOGGER.warning("HA action queue full; dropping control mapping action")
        self.data["control_mappings"] = list(self.control_mapping_engine.mappings)
        self.data["control_mapping_events"] = list(self.control_mapping_events[-20:])
        self.async_set_updated_data(self.data)

    def _execute_ha_mapping(self, proposal: dict) -> None:
        """Translate a normalized mapping proposal into the bounded HA sink."""
        if not self.hass.services.has_service(proposal["domain"], proposal["service"]):
            return
        data = dict(proposal.get("data") or {})
        if proposal.get("entity_id"):
            data["entity_id"] = proposal["entity_id"]
        origin = "dmx_ha_zone" if proposal.get("zone_id") else "dmx_ha_mapping"
        rate = 10.0 if proposal.get("hue_model_id") else None
        if not self._ha_dispatcher.submit(ServiceAction(proposal["domain"], proposal["service"], data, origin, rate), zone_id=str(proposal["zone_id"]) if proposal.get("zone_id") else None):
            _LOGGER.warning("HA action queue full; dropping %s action", origin)

    def _watchdog_event(self, event: str, rule, reason: str) -> None:
        if self.archive:
            self.archive.record("watchdog", event, {"rule": rule.name, "protocol": rule.protocol, "universe": rule.universe, "source": rule.source, "reason": reason})
        severity = "critical" if event == "signal_lost" else "warning" if event == "simulation_loss" else "info"
        message = f"{rule.protocol} univers {rule.universe}" + (f" — {rule.source}" if rule.source else "") + f"\n{reason}"
        notifications = getattr(self, "notifications", None)
        if notifications:
            self.hass.async_create_task(notifications.async_notify("Watchdog", message, severity, f"{rule.name}:{event}"))

    def _watchdog_action_allowed(self, action: dict) -> bool:
        """Apply the same explicit light/scene safety gate to watchdog actions."""
        domain = action.get("domain")
        if domain in {"light", "scene"}:
            return self.light_sync_enabled
        return True

    def _execute_rule_action(self, action) -> None:
        """Execute an explicitly enabled Home Assistant rule action.

        Only Home Assistant service calls are allowed here; no network lighting
        protocol output is generated by the rule engine.
        """
        if not action.domain or not action.service:
            return
        if not self.hass.services.has_service(action.domain, action.service):
            if self.archive:
                self.archive.record("system", "rule_action_failed", {"reason": "service_not_found", "domain": action.domain, "service": action.service, "entity_id": action.entity_id})
            _LOGGER.warning("Rule action service not found: %s.%s", action.domain, action.service)
            return
        # The integration is receive-only for lighting protocols. HA light/scene
        # actions are the only light-sync side effect and require an explicit gate.
        if action.domain in {"light", "scene"} and not self.light_sync_enabled:
            if self.archive:
                self.archive.record("system", "rule_action_blocked", {"rule_gate": "light_sync_disabled", "domain": action.domain, "service": action.service, "entity_id": action.entity_id})
            return
        data = {**action.data, **({"entity_id": action.entity_id} if action.entity_id else {})}
        if not self._ha_dispatcher.submit(ServiceAction(action.domain, action.service, data, "rule")):
            _LOGGER.warning("HA action queue full; dropping rule action")

    async def simulate_signal_loss(self, key: str | None = None) -> None:
        if self.archive:
            self.archive.record("chaos", "signal_loss_injection_start", {"watchdog": key})
        await self.watchdogs.simulate_loss(key)
        self.chaos.start(key or "watchdogs", "signal_loss", "logical only; no network packet suppression")
        if getattr(self, "notifications", None):
            self.hass.async_create_task(self.notifications.async_notify("Chaos", f"Simulation perte de signal — {key or 'tous les watchdogs'}", "warning"))
        self.publish(chaos=self.chaos.snapshot())

    async def simulate_signal_restore(self, key: str | None = None) -> None:
        await self.watchdogs.simulate_restore(key)
        if self.archive:
            self.archive.record("chaos", "signal_restore_injection", {"watchdog": key})
        self.chaos.stop()
        self.publish(chaos=self.chaos.snapshot())

    def simulate_ptp_drift(self, offset_ms: float) -> None:
        value = float(offset_ms)
        self.chaos.start("ptp", "clock_drift", f"simulated offset {value:g} ms")
        if getattr(self, "notifications", None):
            self.hass.async_create_task(self.notifications.async_notify("Chaos", f"Dérive PTP simulée : {value:g} ms", "warning"))
        self.data["ptp_simulated_offset_ms"] = value
        if self.archive:
            self.archive.record("chaos", "ptp_drift_injection", {"offset_ms": value})
        self.publish(chaos=self.chaos.snapshot(), ptp_simulated_offset_ms=value)

    def clear_chaos(self) -> None:
        if self.archive:
            self.archive.record("chaos", "simulation_cleared", {})
        self.chaos.stop()
        self.data.pop("ptp_simulated_offset_ms", None)
        self.publish(chaos=self.chaos.snapshot(), ptp_simulated_offset_ms=None)

    def set_capacity_config(self, **values) -> None:
        for key in self.capacity_config:
            if key in values:
                self.capacity_config[key] = max(0.0, float(values[key]))
        self.publish(network_capacity=capacity_snapshot(self.data.get("dmx_universes", []), **self.capacity_config))

    def save_rules(self) -> None:
        """Persist Rule Builder configuration without runtime state/history."""
        self.rule_store.save(list(self.rules.rules.values()))
        self.config_backups.backup("rule_save")

    def save_dmx_ha_mappings(self) -> None:
        self.dmx_ha_mapping_store.save(self.dmx_ha_mapping_engine.mappings.values())
        self.config_backups.backup("mapping_save")

    def _load_dmx_ha_zones(self) -> None:
        import json
        from pathlib import Path
        path = Path(self.dmx_ha_zone_store_path)
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        for item in raw if isinstance(raw, list) else []:
            try:
                data = dict(item)
                data["channels"] = tuple(data.get("channels", []))
                data["entity_ids"] = tuple(data.get("entity_ids", []))
                data.pop("hue_capabilities", None)
                self.dmx_ha_zone_engine.add(DmxHAZone(**data))
            except (TypeError, ValueError):
                continue

    def save_dmx_ha_zones(self) -> None:
        import json
        from pathlib import Path
        path = Path(self.dmx_ha_zone_store_path)
        path.write_text(json.dumps([z.snapshot() for z in self.dmx_ha_zone_engine.zones.values()], ensure_ascii=False, indent=2), encoding="utf-8")
        self.config_backups.backup("zone_save")

    def set_dmx_ha_zones(self, zones: list[DmxHAZone]) -> None:
        self.dmx_ha_zone_engine.zones.clear()
        for zone in zones:
            self.dmx_ha_zone_engine.add(zone)
        self.save_dmx_ha_zones()
        self.publish(dmx_ha_zones=self.dmx_ha_zone_engine.snapshot(), dmx_ha_rdm=self.dmx_ha_zone_engine.rdm_snapshot())

    def set_light_sync_enabled(self, enabled: bool, require_security: bool = True) -> None:
        """Explicitly arm/disarm HA light/scene actions triggered by rules."""
        if enabled and require_security:
            self.security.require_unlocked()
        self.light_sync_enabled = bool(enabled)
        self.data["light_sync_enabled"] = self.light_sync_enabled
        if self.archive:
            self.archive.record("system", "light_sync_gate_changed", {"enabled": self.light_sync_enabled})
        self.async_set_updated_data(self.data)

    def set_osc_output_enabled(self, enabled: bool, require_security: bool = True) -> None:
        if enabled and require_security:
            self.security.require_unlocked()
        self.osc_output.enabled = bool(enabled)
        self.data["security"] = self.security.snapshot()
        self.data.update({"osc_output_enabled": self.osc_output.enabled})
        self.async_set_updated_data(self.data)

    def save_osc_targets(self) -> None:
        self.osc_target_store.save(list(self.osc_targets.values()))
        self.config_backups.backup("osc_target_save")

    def publish_osc_status(self) -> None:
        self.data.update({
            "osc_output_enabled": self.osc_output.enabled,
            "osc_sent": self.osc_output.sent,
            "osc_errors": self.osc_output.errors,
            "osc_last_target": self.osc_output.last_target,
            "osc_last_address": self.osc_output.last_address,
            "osc_last_error": self.osc_output.last_error,
        })
        self.async_set_updated_data(self.data)

    def publish(self, **updates) -> None:
        """Publish normalized runtime state to the HA coordinator boundary."""
        self.state_store.update(**updates)
        self.data = {**self.data, **updates}
        self.async_set_updated_data(self.data)
