"""Runtime composition for Show Network.

This module owns lifecycle composition only. Protocol implementations remain
in their dedicated modules; Home Assistant integration code does not need to
know how each transport is started or stopped.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from ..backup import ConfigBackupManager
from ..coordinator import ShowNetworkCoordinator
from ..device_inventory import DeviceInventory
from ..archive import EventArchive
from ..gigacore import GigaCoreMonitor
from ..ha_builder import HABuilder
from ..korg import identify_korg_controller
from ..notification_manager import ShowNetworkNotifications
from ..control_mapping import midi_address
from ..protocols import get_adapter_spec
from ..projector import ProjectorController
from ..resource_registry import ProtocolDriver, ResourceRegistry, RuntimeResource
from ..signal_watchdog import SignalWatchdogRule
from ..runtime_data import ShowNetworkRuntimeData
from ..vendor_discovery import async_scan as async_scan_vendor_discovery
from ..discovery_pipeline import DiscoveryPipeline
from ..network_discovery import arp_neighbors
from ..snmp import async_get as async_snmp_get
from ..punchlight_network import async_scan as async_scan_punchlight_network
from ..const import *
from ..aes70_monitor import AES70Monitor
from ..audio_health import AudioHealth
from ..st2110 import ST2110PassiveInspector
from ..audio_health import AudioHealth
from ..performance_manager import AdaptivePerformance

_LOGGER = logging.getLogger(__name__)

def _parse_universes(value):
    """Parse HA universe text (1,2,10-12) into a bounded tuple."""
    out=set()
    for part in str(value or "").replace(" ", "").split(","):
        if not part: continue
        try:
            if "-" in part:
                a,b=(int(x) for x in part.split("-",1)); a,b=min(a,b),max(a,b)
                out.update(range(max(1,a), min(63999,b)+1))
            else:
                n=int(part)
                if 1 <= n <= 63999: out.add(n)
        except ValueError:
            continue
    return tuple(sorted(out))


def _adapter(key: str):
    """Resolve a protocol implementation only through the adapter catalogue."""
    return get_adapter_spec(key).constructor

@dataclass(frozen=True)
class RuntimeSetupResult:
    """All resources created for one config entry."""
    coordinator: ShowNetworkCoordinator
    resources: ResourceRegistry
    inventory: DeviceInventory
    archive: EventArchive
    backup_manager: ConfigBackupManager
    values: dict


async def async_setup_runtime(hass: HomeAssistant, entry: ConfigEntry, settings: dict) -> RuntimeSetupResult:
    """Compose and start protocol/runtime resources for one config entry."""
    # Static fixture YAML must not be read on Home Assistant's event loop.
    from ..fixture_profiles import load_profiles
    await hass.async_add_executor_job(load_profiles)
    # DeviceInventory reads a JSON overrides file synchronously in __init__;
    # run the construction in the executor so that disk I/O never happens
    # directly on the event loop during config entry setup.
    inventory = await hass.async_add_executor_job(
        DeviceInventory, hass.config.path("show_network_device_overrides.json")
    )
    hosts = [h.strip() for h in settings.get(CONF_GIGACORE_HOSTS, "").replace(";", ",").split(",") if h.strip()]
    community = settings.get(CONF_GIGACORE_COMMUNITY, "public")
    gigacore = GigaCoreMonitor(hosts, community)
    coordinator = ShowNetworkCoordinator(hass, inventory, gigacore)
    await hass.async_add_executor_job(coordinator.security.load)
    discovery_pipeline = DiscoveryPipeline(inventory)
    profile = str(settings.get(CONF_PERFORMANCE_PROFILE, "auto")).lower()
    # Auto adapts non-critical work to CPU/RAM pressure; protocol reception remains independent.
    coordinator.performance_manager = AdaptivePerformance(profile)
    coordinator.update_interval = timedelta(seconds=5)
    resources = ResourceRegistry()
    coordinator.resource_registry = resources
    coordinator.ha_builder_enabled = bool(settings.get(CONF_HA_BUILDER_ENABLED, True))
    # Same reasoning as DeviceInventory above: HABuilder.__init__ loads a JSON
    # file synchronously, so build it off the event loop.
    coordinator.ha_builder = await hass.async_add_executor_job(
        HABuilder, hass.config.path("show_network_ha_builder.json")
    )
    coordinator.notifications = ShowNetworkNotifications(
        hass, settings.get(CONF_NOTIFICATION_TARGET, "persistent"),
        bool(settings.get(CONF_NOTIFICATION_ENABLED, False)),
        str(settings.get(CONF_NOTIFICATION_MODE, "both")),
    )
    coordinator.set_capacity_config(
        link_mbps=float(settings.get(CONF_CAPACITY_LINK_MBPS, 1000)),
        dante_mbps=float(settings.get(CONF_CAPACITY_DANTE_MBPS, 0)),
        cameras_mbps=float(settings.get(CONF_CAPACITY_CAMERAS_MBPS, 0)),
        st2110_mbps=float(settings.get(CONF_CAPACITY_ST2110_MBPS, 0)),
        other_mbps=float(settings.get(CONF_CAPACITY_OTHER_MBPS, 0)),
    )
    coordinator.audio_health = AudioHealth()
    coordinator.projector_controller = ProjectorController(control_enabled=False)
    from ..projector_monitor import PJLinkMonitor
    raw_projectors = settings.get("projectors", [])
    if isinstance(raw_projectors, str):
        try: raw_projectors = json.loads(raw_projectors)
        except Exception: raw_projectors = []
    coordinator.projector_monitor_enabled = bool(settings.get(CONF_PROJECTOR_MONITOR_ENABLED, True))
    coordinator.projector_monitor = PJLinkMonitor((raw_projectors if isinstance(raw_projectors, list) else []) if coordinator.projector_monitor_enabled else [])
    coordinator.chaos_enabled = bool(settings.get(CONF_CHAOS_ENABLED, False))

    interface = settings.get(CONF_INTERFACE_DMX, settings.get(CONF_INTERFACE, "0.0.0.0"))
    interface_ma = settings.get(CONF_INTERFACE_MA, interface)
    interface_ptp = settings.get(CONF_INTERFACE_PTP, interface)
    interface_dante = settings.get(CONF_INTERFACE_DANTE, interface)
    interface_audio = settings.get(CONF_INTERFACE_AUDIO, interface)
    interface_osc = settings.get(CONF_OSC_INPUT_INTERFACE, interface)

    # Publish the effective Show Network binding configuration so the custom
    # panel can show exactly which NIC each protocol is using.  This contains
    # no credentials.
    coordinator.data["show_network_config"] = {
        "interface_default": settings.get(CONF_INTERFACE, "0.0.0.0"),
        "interface_dmx": interface,
        "interface_ma": interface_ma,
        "interface_ptp": interface_ptp,
        "interface_dante": interface_dante,
        "interface_audio": interface_audio,
        "interface_osc": interface_osc,
        "universes": settings.get(CONF_UNIVERSES, "1-16"),
        "dmx_artnet_enabled": bool(settings.get(CONF_DMX_ARTNET_ENABLED, True)),
        "dmx_sacn_enabled": bool(settings.get(CONF_DMX_SACN_ENABLED, True)),
        "dmx_source": str(settings.get(CONF_DMX_SOURCE, "") or ""),
        "ma_enabled": bool(settings.get(CONF_MA_ENABLED, True)),
        "osc_input_enabled": bool(settings.get(CONF_OSC_INPUT_ENABLED, False)),
        "osc_input_port": int(settings.get(CONF_OSC_INPUT_PORT, 8000)),
        "midi_enabled": bool(settings.get(CONF_MIDI_ENABLED, False)),
        "punchlight_enabled": bool(settings.get(CONF_PUNCHLIGHT_ENABLED, False)),
        "watchdog_enabled": bool(settings.get(CONF_WATCHDOG_ENABLED, False)),
        "ha_builder_enabled": bool(settings.get(CONF_HA_BUILDER_ENABLED, True)),
        "notification_enabled": bool(settings.get(CONF_NOTIFICATION_ENABLED, False)),
        "projector_monitor_enabled": coordinator.projector_monitor_enabled,
        "chaos_enabled": coordinator.chaos_enabled,
    }

    ma_listener = None
    if bool(settings.get(CONF_MA_ENABLED, True)) and interface_ma != "0.0.0.0":
        ma_listener = _adapter("ma-net3")(interface_ma, port=MA_NET3_PORT)
        try: await ma_listener.start()
        except Exception as err:
            _LOGGER.warning("MA-Net3 listener unavailable; continuing without it: %s", err); ma_listener = None
    coordinator.ma_listener = ma_listener
    if ma_listener: resources.add(RuntimeResource(ProtocolDriver("ma-net3", "LIGHT"), "ma-net3", ma_listener, "stop", {"interface": interface_ma, "role": "listener"}))

    ptp_monitor = _adapter("ptp")(interface_ptp if interface_ptp != "0.0.0.0" else "0.0.0.0")
    try: await ptp_monitor.start()
    except Exception as err:
        _LOGGER.warning("PTP monitor unavailable; continuing without it: %s", err); ptp_monitor = None
    coordinator.ptp_monitor = ptp_monitor
    if ptp_monitor: resources.add(RuntimeResource(ProtocolDriver("ptp", "AUDIO"), "ptp", ptp_monitor, "stop", {"interface": interface_ptp, "role": "monitor"}))

    archive = EventArchive(hass.config.path(), retention_days=int(settings.get(CONF_ARCHIVE_RETENTION_DAYS, 30)), max_bytes=int(settings.get(CONF_ARCHIVE_MAX_BYTES, 5 * 1024 * 1024)), destination=settings.get(CONF_ARCHIVE_DESTINATION, "show_network_archive"))
    coordinator.archive = archive
    await archive.async_start()
    archive.record("system", "integration_start", {"entry_id": entry.entry_id})
    backup_manager = ConfigBackupManager(hass.config.path(), keep=10)
    await hass.async_add_executor_job(backup_manager.backup, "startup")
    await hass.async_add_executor_job(archive.export_zip)
    async def _archive_periodic(_now): await hass.async_add_executor_job(archive.export_zip)
    archive_backup_cancel = async_track_time_interval(hass, _archive_periodic, timedelta(hours=6))
    async def _config_backup_periodic(_now): await hass.async_add_executor_job(backup_manager.backup, "scheduled")
    backup_cancel = async_track_time_interval(hass, _config_backup_periodic, timedelta(hours=6))

    if settings.get(CONF_WATCHDOG_ENABLED, False):
        loss_scene = settings.get(CONF_WATCHDOG_LOSS_SCENE, "").strip(); recovery_scene = settings.get(CONF_WATCHDOG_RECOVERY_SCENE, "").strip()
        coordinator.watchdogs.add_rule(SignalWatchdogRule(name="DMX signal watchdog", protocol=settings.get(CONF_WATCHDOG_PROTOCOL, "ENTTEC"), universe=int(settings.get(CONF_WATCHDOG_UNIVERSE, 1)), source=settings.get(CONF_WATCHDOG_SOURCE, "").strip() or None, loss_timeout_s=float(settings.get(CONF_WATCHDOG_TIMEOUT, 10)), recovery_delay_s=float(settings.get(CONF_WATCHDOG_RECOVERY_DELAY, 3)), loss_action={"domain":"scene","service":"turn_on","entity_id":loss_scene} if loss_scene else None, recovery_action={"domain":"scene","service":"turn_on","entity_id":recovery_scene} if recovery_scene else None))

    dante_monitor = _adapter("dante")(interface_dante if interface_dante != "0.0.0.0" else "0.0.0.0")
    try: await dante_monitor.start()
    except Exception as err:
        _LOGGER.warning("Dante monitor unavailable; continuing without it: %s", err); dante_monitor = None
    coordinator.dante_monitor = dante_monitor
    if dante_monitor: resources.add(RuntimeResource(ProtocolDriver("dante", "AUDIO"), "dante", dante_monitor, "stop", {"interface": interface_dante, "role": "monitor"}))
    aes67_monitor = _adapter("aes67")(interface_audio if interface_audio != "0.0.0.0" else "0.0.0.0")
    try: await aes67_monitor.start()
    except Exception as err:
        _LOGGER.warning("AES67 monitor unavailable; continuing without it: %s", err); aes67_monitor = None
    coordinator.aes67_monitor = aes67_monitor
    coordinator.aes70_monitor = None
    aes70_hosts = [h.strip() for h in str(settings.get(CONF_AES70_HOSTS, "")).replace(";", ",").split(",") if h.strip()]
    if aes70_hosts:
        aes70_monitor = AES70Monitor(aes70_hosts, port=int(settings.get(CONF_AES70_PORT, 65000)))
        try:
            await aes70_monitor.start()
            coordinator.aes70_monitor = aes70_monitor
            resources.add(RuntimeResource(ProtocolDriver("aes70", "AUDIO"), "aes70", aes70_monitor, "stop", {"hosts": aes70_hosts, "port": int(settings.get(CONF_AES70_PORT, 65000)), "role": "active-protocol-monitor"}))
        except Exception as err:
            _LOGGER.warning("AES70 monitor unavailable; continuing without it: %s", err)
            aes70_monitor = None
    if aes67_monitor: resources.add(RuntimeResource(ProtocolDriver("aes67", "AUDIO"), "aes67", aes67_monitor, "stop", {"interface": interface_audio, "role": "monitor"}))
    coordinator.st2110_monitor = ST2110PassiveInspector(); coordinator.avb_monitor = _adapter("avb")()

    enttec_input = None; enttec_device = settings.get(CONF_ENTTEC_DEVICE, "").strip()
    if enttec_device:
        enttec_input = _adapter("enttec")(enttec_device, entry.data.get(CONF_ENTTEC_MODEL, "auto"), on_frame=lambda values: coordinator.observe_dmx("ENTTEC", 1, enttec_device, values))
        try: await enttec_input.start()
        except Exception as err:
            _LOGGER.warning("ENTTEC input unavailable; continuing without it: %s", err); enttec_input = None
    coordinator.enttec_input = enttec_input
    if enttec_input: resources.add(RuntimeResource(ProtocolDriver("enttec", "LIGHT"), "enttec", enttec_input, "stop", {"device": enttec_device, "role": "receive-only"}))

    punchlight = None
    if settings.get(CONF_PUNCHLIGHT_ENABLED, False) and settings.get(CONF_PUNCHLIGHT_DEVICE, "").strip():
        async def _punchlight_changed(state: dict):
            previous = coordinator.data.get("punchlight", {}); coordinator.publish(punchlight=state); actions=[]
            transitions=(("recording",CONF_PUNCHLIGHT_RECORD_SCENE,CONF_PUNCHLIGHT_STOP_SCENE),("ready",CONF_PUNCHLIGHT_READY_SCENE,CONF_PUNCHLIGHT_NOT_READY_SCENE))
            for field,on_key,off_key in transitions:
                changed=bool(state.get(field)) != bool(previous.get(field))
                if changed:
                    scene_key=on_key if state.get(field) else off_key; scene=settings.get(scene_key, "").strip()
                    if scene: actions.append(scene)
            for entity_id in actions:
                try: await hass.services.async_call("scene","turn_on",{"entity_id":entity_id},blocking=False)
                except Exception as err: _LOGGER.warning("PunchLight scene %s failed: %s",entity_id,err)
        punchlight = _adapter("punchlight")(settings.get(CONF_PUNCHLIGHT_DEVICE, "").strip(), _punchlight_changed, source_name="punchlight")
        try: await punchlight.async_start()
        except Exception as err: _LOGGER.warning("PunchLight monitor unavailable; continuing without it: %s",err); punchlight=None

    osc_receiver=None
    if bool(settings.get(CONF_OSC_INPUT_ENABLED,False)):
        osc_host=interface_osc or "0.0.0.0"; osc_port=int(settings.get(CONF_OSC_INPUT_PORT,8000))
        def _osc_input(message):
            coordinator.data["osc_messages"]=int(coordinator.data.get("osc_messages",0))+1
            coordinator.data["osc_input"]={"enabled":True,"messages":coordinator.data["osc_messages"],"last_address":message.address,"last_source":message.source[0] if message.source else None,"last_error":None}
            coordinator.data["osc_learn"]={"active":bool(coordinator.osc_learn.active),"suggestions":coordinator.osc_learn.suggestions()}
            for value in message.values:
                if isinstance(value,(int,float)) and not isinstance(value,bool): coordinator.process_control_input(message.address,value)
            coordinator.async_set_updated_data(coordinator.data)
        osc_receiver=_adapter("osc")(host=osc_host,port=osc_port,learn=coordinator.osc_learn,callback=_osc_input)
        try:
            await osc_receiver.start()
            coordinator.data["osc_input"]={**coordinator.data.get("osc_input",{}),"enabled":True,"state":"listening","host":osc_host,"port":osc_port,"last_error":None}
        except OSError as err:
            # A config-entry reload can briefly overlap kernel UDP teardown. Retry
            # once, then expose the conflict instead of pretending OSC is enabled.
            if getattr(err, "errno", None) == 98:
                await asyncio.sleep(0.5)
                try:
                    await osc_receiver.start()
                    coordinator.data["osc_input"]={**coordinator.data.get("osc_input",{}),"enabled":True,"state":"listening","host":osc_host,"port":osc_port,"last_error":None}
                except Exception as retry_err:
                    coordinator.data["osc_input"]={"enabled":False,"state":"port_in_use","host":osc_host,"port":osc_port,"last_error":str(retry_err)}
                    _LOGGER.warning("OSC input unavailable after retry; port %s is in use: %s",osc_port,retry_err); osc_receiver=None
            else:
                coordinator.data["osc_input"]={"enabled":False,"state":"error","host":osc_host,"port":osc_port,"last_error":str(err)}
                _LOGGER.warning("OSC input unavailable; continuing without it: %s",err); osc_receiver=None
        except Exception as err:
            coordinator.data["osc_input"]={"enabled":False,"state":"error","host":osc_host,"port":osc_port,"last_error":str(err)}
            _LOGGER.warning("OSC input unavailable; continuing without it: %s",err); osc_receiver=None

    midi_runtime=None; midi_controller=None
    if bool(settings.get(CONF_MIDI_ENABLED,False)) and str(settings.get(CONF_MIDI_DEVICE,"")).strip():
        async def _midi_input(message):
            address=midi_address(message)
            if not address or not message.data: return
            value=message.data[-1]; coordinator.data["midi_input"]={"enabled":True,"connected":True,"messages":int(coordinator.data.get("midi_input",{}).get("messages",0))+1,"port":message.source,"last_error":None}; coordinator.process_control_input(address,value)
        midi_port=str(settings[CONF_MIDI_DEVICE]); midi_controller=identify_korg_controller(midi_port); midi_runtime=_adapter("midi")(midi_port,_midi_input,source_name=midi_port)
        if not await midi_runtime.async_start(): _LOGGER.warning("MIDI input unavailable; continuing without it: %s",midi_runtime.error); midi_runtime=None
    coordinator.data["midi_input"]={**coordinator.data.get("midi_input",{}),"enabled":bool(midi_runtime),"connected":bool(midi_runtime),"port":settings.get(CONF_MIDI_DEVICE) if midi_runtime else None,"controller":midi_controller.model if midi_controller else None,"manufacturer":midi_controller.manufacturer if midi_controller else None}
    if osc_receiver: resources.add(RuntimeResource(ProtocolDriver("osc-input","CONTROL"),"osc-input",osc_receiver,"stop",{"role":"receive-only","interface":settings.get(CONF_OSC_INPUT_INTERFACE,interface),"port":int(settings.get(CONF_OSC_INPUT_PORT,8000))}))
    if midi_runtime: resources.add(RuntimeResource(ProtocolDriver("midi-input","CONTROL"),"midi-input",midi_runtime,"async_stop",{"role":"receive-only","port":settings.get(CONF_MIDI_DEVICE)}))
    coordinator.punchlight=punchlight
    if punchlight: resources.add(RuntimeResource(ProtocolDriver("punchlight","CONTROL"),"punchlight",punchlight,"async_stop",{"role":"receive-only","transport":"MIDI endpoint selected by host"}))

    coordinator.data["punchlight_network"]=[]
    dmx_network=_adapter("dmx-network")(
        interface,
        on_frame=lambda protocol,universe,source,values,priority,sequence,iface: coordinator.observe_dmx(protocol,universe,source,values,priority,sequence,iface),
        on_timecode=lambda data,source:(coordinator.timecode.observe_artnet(data,source) and coordinator.publish(timecode=coordinator.timecode.snapshot())),
        multicast_universes=_parse_universes(settings.get(CONF_UNIVERSES, "1-16")),
        artnet_enabled=bool(settings.get(CONF_DMX_ARTNET_ENABLED, True)),
        sacn_enabled=bool(settings.get(CONF_DMX_SACN_ENABLED, True)),
        source_filter=str(settings.get(CONF_DMX_SOURCE, "") or "").strip() or None,
    )
    try: await dmx_network.start()
    except Exception as err: _LOGGER.warning("DMX network receiver unavailable; continuing without it: %s",err); dmx_network=None
    coordinator.dmx_network=dmx_network
    if dmx_network: resources.add(RuntimeResource(ProtocolDriver("dmx-network","LIGHT"),"dmx-network",dmx_network,"stop",{"interface":interface,"role":"receive-only"}))
    coordinator.data["switch_manufacturers"]=settings.get("switch_manufacturers",["luminex","elc","green_go"])
    coordinator.set_light_sync_enabled(bool(settings.get(CONF_LIGHT_SYNC_ENABLED,False)),require_security=False)
    coordinator.data["ha_builder"]=coordinator.ha_builder.snapshot() if coordinator.ha_builder_enabled else []
    coordinator.data["ha_builder_enabled"]=coordinator.ha_builder_enabled
    coordinator.data["notification"]={"enabled":coordinator.notifications.enabled,"target":coordinator.notifications.target,"mode":coordinator.notifications.mode}

    async def _vendor_discovery_tick(_now=None):
        status = {"state": "running", "mdns_state": "scanning", "mdns_services": 0, "mdns_detail": "using Home Assistant shared Zeroconf; passive DNS-SD scan in progress", "mdns_timeout_s": 2.0, "arp_neighbors": 0, "inventory_total": len(coordinator.inventory.devices), "errors": []}
        coordinator.publish(discovery_status=status)
        rows = []
        try:
            rows = await async_scan_vendor_discovery(hass, 2.0)
            coordinator.vendor_discovery = rows[-200:]
            status["mdns_services"] = len(rows)
            status["mdns_state"] = "observed" if rows else "no_services_observed"
            status["mdns_detail"] = (f"{len(rows)} mDNS service(s) observed via Home Assistant shared Zeroconf" if rows else "shared Zeroconf active; no mDNS service observed during the 2.0 s passive scan window")
            for row in rows:
                addresses = row.get("addresses") or []
                host = (addresses[0] if addresses else None) or row.get("host") or row.get("name")
                if host:
                    discovery_pipeline.mdns_result(host, row.get("service_type", ""), row.get("name", ""), row.get("properties") or {})
                if row.get("vendor") == "green_go":
                    coordinator.green_go.observe(host, source="mdns", evidence=row.get("evidence"), last_seen=row.get("observed_at"))
                elif row.get("vendor") == "elc":
                    coordinator.elc.observe(host, source="mdns", evidence=row.get("evidence"), last_seen=row.get("observed_at"))
                elif row.get("vendor") in ("dante", "luminex"):
                    vendor = row.get("vendor")
                    addresses = row.get("addresses") or []
                    ip = addresses[0] if addresses else None
                    coordinator.inventory.upsert(
                        ip=ip, hostname=row.get("host") or row.get("name"),
                        manufacturer=("Audinate/Dante" if vendor == "dante" else "Luminex"),
                        category=("audio_network" if vendor == "dante" else "network_switch"),
                        protocols=({"mDNS", "Dante"} if vendor == "dante" else {"mDNS"}),
                        sources={"mdns"}, confidence="confirmed", confidence_score=.95,
                        evidence=[{"field":"service_type","value":row.get("service_type"),"source":"mdns","confidence":1.0}],
                        unique_id=f"mdns:{ip or host}",
                    )
        except Exception as err:
            status["mdns_state"] = "error"
            status["mdns_detail"] = f"{type(err).__name__}: {err}"
            status["errors"].append(f"mDNS: {err}")
            _LOGGER.warning("Show Network mDNS discovery failed: %s", err)
        try:
            neighbors = await hass.async_add_executor_job(arp_neighbors)
            status["arp_neighbors"] = len(neighbors)
            for row in neighbors:
                coordinator.inventory.upsert(
                    ip=row.get("ip"), mac=row.get("mac"), protocols={"IPv4/ARP"},
                    sources={"arp_cache"}, confidence="candidate", confidence_score=0.65,
                    evidence=[{"field":"interface","value":row.get("interface"),"source":"arp_cache","confidence":0.9}],
                    unique_id=f"candidate:{row.get('ip')}",
                )
            # Read-only SNMP identity enrichment.  This is deliberately bounded and
            # uses only the community explicitly configured by the user.  A timeout is
            # not evidence that the host is not a switch.
            community = str(settings.get(CONF_GIGACORE_COMMUNITY, "") or "").strip()
            # Luminex documents read-only SNMP v1/v2c with default community "Public".
            # Use that conservative read-only probe when no community was configured;
            # a timeout remains unknown, never evidence that a host is not a switch.
            community = community or "Public"
            status["snmp_probe_mode"] = "configured" if settings.get(CONF_GIGACORE_COMMUNITY) else "readonly_default_public"
            if community:
                sem = asyncio.Semaphore(4)
                status["snmp_hosts"] = []
                vendor_markers = (
                    ("Luminex", ("luminex", "gigacore")),
                    ("ELC Lighting", ("dmxlan", "elc lighting")),
                    ("Green-GO", ("green-go", "greengo")),
                    ("Cisco", ("cisco", "catalyst")),
                    ("HPE Aruba", ("aruba", "procurve", "hewlett packard enterprise", "hpe officeconnect")),
                    ("NETGEAR", ("netgear",)),
                    ("Ubiquiti", ("ubiquiti", "unifi switch", "edgeswitch")),
                    ("MikroTik", ("mikrotik", "routeros")),
                    ("TP-Link", ("tp-link", "tplink", "jetstream", "omada")),
                    ("Allied Telesis", ("allied telesis",)),
                    ("Juniper", ("juniper",)),
                )
                async def _snmp_identity(row):
                    ip = row.get("ip")
                    if not ip: return
                    result = {"ip": ip, "state": "timeout_or_no_snmp", "manufacturer": None, "sys_name": None, "sys_descr": None, "sys_object_id": None}
                    async with sem:
                        descr, name, obj = await asyncio.gather(
                            async_snmp_get(ip, community, "1.3.6.1.2.1.1.1.0", timeout=.65),
                            async_snmp_get(ip, community, "1.3.6.1.2.1.1.5.0", timeout=.65),
                            async_snmp_get(ip, community, "1.3.6.1.2.1.1.2.0", timeout=.65),
                        )
                    if descr is None and name is None and obj is None:
                        status["snmp_hosts"].append(result); return
                    text = f"{descr or ''} {name or ''} {obj or ''}".lower()
                    manufacturer = next((vendor for vendor, markers in vendor_markers if any(m in text for m in markers)), None)
                    switch_evidence = bool(manufacturer) or any(x in text for x in ("switch", "ethernet switch", "managed switch", "gigabit ethernet"))
                    model = str(descr) if descr else None
                    result.update({"state":"responded", "manufacturer":manufacturer, "sys_name":name, "sys_descr":descr, "sys_object_id":obj, "switch_evidence":switch_evidence})
                    status["snmp_hosts"].append(result)
                    dev = coordinator.inventory.find_by_ip(ip)
                    coordinator.inventory.upsert(
                        unique_id=(dev.unique_id if dev else f"candidate:{ip}"), ip=ip,
                        hostname=(str(name) if name else None), manufacturer=manufacturer, model=model,
                        category=("network_switch" if switch_evidence else "network_device"), protocols={"IPv4/ARP", "SNMP"}, sources={"snmp_readonly"},
                        confidence=("confirmed" if manufacturer else "candidate"),
                        confidence_score=(.96 if manufacturer else .8),
                        evidence=[
                            {"field":"sysDescr","value":descr,"source":"snmp","confidence":1.0},
                            {"field":"sysName","value":name,"source":"snmp","confidence":1.0},
                            {"field":"sysObjectID","value":obj,"source":"snmp","confidence":1.0},
                        ],
                    )
                await asyncio.gather(*(_snmp_identity(r) for r in neighbors))
                status["snmp_hosts"].sort(key=lambda x: x.get("ip") or "")
                status["snmp_attempted"] = len(status["snmp_hosts"])
                status["snmp_responders"] = sum(1 for x in status["snmp_hosts"] if x.get("state") == "responded")
                status["identified_switches"] = sum(1 for d in coordinator.inventory.devices.values() if d.category == "network_switch")
            else:
                status["snmp_state"] = "not_configured"
        except Exception as err:
            status["errors"].append(f"ARP: {err}")
            _LOGGER.warning("Show Network ARP discovery failed: %s", err)
        status["inventory_total"] = len(coordinator.inventory.devices)
        status["state"] = "error" if status["errors"] and not (status["mdns_services"] or status["arp_neighbors"]) else "complete"
        coordinator.publish(
            discovery_status=status, vendor_discovery=coordinator.vendor_discovery,
            device_inventory=coordinator.inventory.public(include_hidden=True),
            green_go_inventory=coordinator.green_go.snapshot(), elc_inventory=coordinator.elc.snapshot(),
        )
    coordinator.async_scan_network = _vendor_discovery_tick
    vendor_discovery_cancel=async_track_time_interval(hass,_vendor_discovery_tick,timedelta(seconds=180))
    # Run the first scan in the background instead of awaiting it inline: this
    # scan takes >=2s and was previously blocking async_setup_entry directly,
    # contributing to slow/timed-out config entry bootstraps.
    hass.async_create_background_task(_vendor_discovery_tick(), name="show_network_initial_vendor_discovery")
    async def _punchlight_periodic_discovery(_now):
        try:
            devices=await async_scan_punchlight_network(hass, interface, timeout=2.0)
            coordinator.publish(punchlight_network=devices)
        except Exception as err: _LOGGER.debug("PunchLight network discovery failed: %s",err)
    punchlight_discovery_cancel=async_track_time_interval(hass,_punchlight_periodic_discovery,timedelta(seconds=PUNCHLIGHT_DISCOVERY_INTERVAL_S))
    coordinator.async_start_workers(); await coordinator.async_config_entry_first_refresh()

    values={"inventory":inventory,"resource_registry":resources,"coordinator":coordinator,"ma_listener":ma_listener,"ptp_monitor":ptp_monitor,"dante_monitor":dante_monitor,"aes67_monitor":aes67_monitor,"st2110_monitor":coordinator.st2110_monitor,"avb_monitor":coordinator.avb_monitor,"archive":archive,"enttec_input":enttec_input,"punchlight":punchlight,"osc_receiver":osc_receiver,"midi_runtime":midi_runtime,"dmx_network":dmx_network,"backup_cancel":backup_cancel,"archive_backup_cancel":archive_backup_cancel,"vendor_discovery_cancel":vendor_discovery_cancel,"punchlight_discovery_cancel":punchlight_discovery_cancel}
    return RuntimeSetupResult(coordinator,resources,inventory,archive,backup_manager,values)
