"""Composition root: turns config entry settings into a running coordinator.

This is the piece that was missing from the delivered zip: coordinator.py
already has every feature's logic and a ``self.xxx = None`` placeholder for
every optional monitor, but nothing ever read the config entry and actually
constructed those monitors. That is exactly what ``async_setup_runtime``
does below, one subsystem at a time, gated by the same CONF_* constants
already defined in const.py and already exposed in config_flow.py.

Every network listener is started through ``_try_start`` so that one
misconfigured/unreachable service (a bad interface, a switch that is
temporarily off) cannot prevent the whole integration from loading -- it is
logged and skipped, exactly like the rest of this codebase's
never-crash-on-a-bad-value philosophy.

Design notes carried over from the audit:
- Tally IP (TSL UMD) has config fields and an entity but no listener
  anywhere in this codebase; it is deliberately NOT wired here yet. Wiring
  it would require writing that listener first.
- RDM/RDMnet are wired as HTTP bridge clients (rdm_bridge_client.py),
  matching CONF_RDM_BRIDGE_URL/CONF_RDMNET_BRIDGE_URL exactly the same way
  CONF_AVDECC_BRIDGE_URL already implied for AVDECC.
- Full automatic switch discovery (matching switch_profiles against
  ARP-scanned, SNMP-responsive hosts) does not exist as a feature anywhere
  in this codebase; only GigaCore's explicit host list
  (CONF_GIGACORE_HOSTS) is wired to a real monitor here.
- Incoming OSC/MIDI currently has no action-mapping consumer:
  control_mapping.py/osc_mapping.py implement one (MappingEngine) but were
  never imported by coordinator.py either -- another audit finding, not
  fixed here to keep this file's scope to composition, not new features.
  OSC still feeds OSC Learn mode, which is useful on its own.
- The projector JSON config list and the HABuilder/dynamic-entity wiring
  are intentionally left for the platform files (sensor.py) to finish,
  since they are entity-registration concerns, not runtime composition.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .. import const
from ..device_inventory import DeviceInventory
from ..coordinator import ShowNetworkCoordinator
from ..gigacore import GigaCoreMonitor
from ..dante import DanteMonitor
from ..aes67 import AES67Monitor
from ..audio_ptp import PTPMonitor
from ..aes70_monitor import AES70Monitor
from ..avdecc_bridge import AVDECCBridgeMonitor
from ..rdm_bridge_client import RDMBridgeMonitor
from ..ma_net3_listener import MANet3Listener
from ..lighting_receiver import DmxNetworkReceiver
from ..enttec import EnttecDmxInput
from ..osc_receiver import OSCReceiver
from ..midi_runtime import MIDIInputRuntime
from ..punchlight import PunchLightState
from ..etc_cem3 import CEM3WebMonitor
from ..st2110 import ST2110PassiveInspector
from ..artnet_discovery import async_send_poll
from ..notification_manager import ShowNetworkNotifications
from ..signal_watchdog import WatchdogRule
from ..archive import EventArchive
from ..ha_builder import HABuilder
from .resource_registry import ResourceRegistry

_LOGGER = logging.getLogger(__name__)


@dataclass
class Runtime:
    coordinator: ShowNetworkCoordinator
    resources: ResourceRegistry
    archive: EventArchive | None
    backup_manager: Any
    values: dict[str, Any] = field(default_factory=dict)


def _parse_host_list(raw: Any) -> list[str]:
    """Parse a comma/whitespace-separated host-list config field (see
    CONF_GIGACORE_HOSTS/CONF_AES70_HOSTS/CONF_ETC_CEM3_HOSTS in config_flow.py,
    all declared as a plain ``str``)."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(h).strip() for h in raw if str(h).strip()]
    return [h.strip() for h in str(raw).replace(",", " ").split() if h.strip()]


async def _try_start(name: str, obj: Any, resources: ResourceRegistry, *, stop_method: str = "stop") -> bool:
    """Start ``obj`` (an object with an async ``start()``), registering it
    for shutdown only on success. Never raises: a failed listener is logged
    and skipped rather than aborting the whole config entry setup."""
    try:
        await obj.start()
    except Exception as exc:
        _LOGGER.warning("Could not start %s: %s", name, exc)
        return False
    resources.register(name, obj, stop_method=stop_method)
    return True


class _PeriodicArtPoll:
    """Sends an ArtPoll broadcast every ``interval_s`` seconds.

    A harmless discovery broadcast, not a control action -- see
    artnet_discovery.py's module docstring. Node replies arrive through the
    normal DMX receiver's on_poll_reply callback, not here; this only
    triggers them to answer periodically (nodes don't announce themselves
    unprompted the way SAP/mDNS devices do).
    """

    def __init__(self, interface: str, interval_s: float = 30.0) -> None:
        self.interface = interface
        self.interval_s = interval_s
        self._task: Any = None

    async def start(self) -> None:
        import asyncio
        self._task = asyncio.create_task(self._loop(), name="show-network-artpoll")

    async def _loop(self) -> None:
        import asyncio
        while True:
            try:
                await async_send_poll(self.interface)
            except Exception as exc:
                _LOGGER.debug("ArtPoll broadcast failed: %s", exc)
            await asyncio.sleep(self.interval_s)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            import asyncio
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None


async def async_setup_runtime(hass: HomeAssistant, entry: ConfigEntry, settings: dict[str, Any]) -> Runtime:
    resources = ResourceRegistry()
    default_interface = settings.get(const.CONF_INTERFACE, "0.0.0.0")

    # -- GigaCore (Luminex, private OIDs) -------------------------------------
    gigacore_hosts = _parse_host_list(settings.get(const.CONF_GIGACORE_HOSTS))
    gigacore = None
    if gigacore_hosts:
        gigacore = GigaCoreMonitor(gigacore_hosts, settings.get(const.CONF_GIGACORE_COMMUNITY, const.DEFAULT_GIGACORE_COMMUNITY))

    # -- Coordinator itself ----------------------------------------------------
    inventory = DeviceInventory(hass.config.path("show_network_device_inventory.json"))
    coordinator = ShowNetworkCoordinator(hass, inventory, gigacore=gigacore)
    # NOTE (audit finding while writing sensor.py/switch.py/number.py):
    # binary_sensor.py's real async_setup_entry() does
    # `coordinator.ha_builder.items.values()` with no getattr/None guard, so
    # this must always exist -- CONF_HA_BUILDER_ENABLED only gates whether
    # new items can be *created* later (see services.py), not whether the
    # registry object itself is present.
    coordinator.ha_builder = HABuilder(hass.config.path("show_network_ha_builder.json"))
    coordinator.ha_builder_enabled = bool(settings.get(const.CONF_HA_BUILDER_ENABLED, True))
    # GigaCoreMonitor has no start()/stop() lifecycle of its own -- it is
    # polled from coordinator's own refresh cycle (async_update()), same
    # pattern as CEM3WebMonitor below -- so nothing to register here.

    # -- DMX scene bank repeat-output worker (previously never started) -----------------
    await _try_start("dmx_scene_bank", coordinator.dmx_scene_bank, resources)

    # -- Notifications (always constructed; enabled flag gates sending) --------
    coordinator.notifications = ShowNetworkNotifications(
        hass,
        target=settings.get(const.CONF_NOTIFICATION_TARGET),
        enabled=bool(settings.get(const.CONF_NOTIFICATION_ENABLED, False)),
        mode=settings.get(const.CONF_NOTIFICATION_MODE, "both"),
    )

    # -- Archive ------------------------------------------------------------------
    archive = EventArchive(
        hass.config.path(),
        retention_days=int(settings.get(const.CONF_ARCHIVE_RETENTION_DAYS, 7)),
        max_bytes=int(settings.get(const.CONF_ARCHIVE_MAX_BYTES, 5 * 1024 * 1024)),
        destination=settings.get(const.CONF_ARCHIVE_DESTINATION),
    )
    await archive.async_start()
    coordinator.archive = archive
    resources.register("archive", archive, stop_method="async_stop")

    # -- DMX reception (core feature, always on) -----------------------------------
    dmx_interface = settings.get(const.CONF_INTERFACE_DMX, default_interface)
    dmx_network = DmxNetworkReceiver(
        dmx_interface,
        on_frame=coordinator.observe_dmx,
        on_timecode=coordinator.timecode.observe,
        on_poll_reply=coordinator.artnet_nodes.observe_poll_reply,
        artnet_enabled=bool(settings.get(const.CONF_DMX_ARTNET_ENABLED, True)),
        sacn_enabled=bool(settings.get(const.CONF_DMX_SACN_ENABLED, True)),
        source_filter=settings.get(const.CONF_DMX_SOURCE),
    )
    if await _try_start("dmx_network", dmx_network, resources):
        coordinator.dmx_network = dmx_network

    artpoll = _PeriodicArtPoll(dmx_interface)
    await _try_start("artpoll_broadcaster", artpoll, resources)

    # -- ENTTEC USB DMX input ------------------------------------------------------
    enttec_device = settings.get(const.CONF_ENTTEC_DEVICE)
    if enttec_device:
        def _on_enttec_frame(values: bytes) -> None:
            coordinator.observe_dmx("ENTTEC", 1, enttec_device, values)

        enttec_input = EnttecDmxInput(enttec_device, model=settings.get(const.CONF_ENTTEC_MODEL, "auto"), on_frame=_on_enttec_frame)
        if await _try_start("enttec_input", enttec_input, resources):
            coordinator.enttec_input = enttec_input

    # -- Dante / AES67 / PTP (audio IP, always on if an interface is set) ----------
    dante_monitor = DanteMonitor(interface=settings.get(const.CONF_INTERFACE_DANTE, default_interface))
    if await _try_start("dante_monitor", dante_monitor, resources):
        coordinator.dante_monitor = dante_monitor

    aes67_monitor = AES67Monitor(interface=settings.get(const.CONF_INTERFACE_AUDIO, default_interface))
    if await _try_start("aes67_monitor", aes67_monitor, resources):
        coordinator.aes67_monitor = aes67_monitor

    ptp_monitor = PTPMonitor(interface=settings.get(const.CONF_INTERFACE_PTP, default_interface))
    if await _try_start("ptp_monitor", ptp_monitor, resources):
        coordinator.ptp_monitor = ptp_monitor

    # -- AES70/OCA (active TCP controller; explicit host list required) -----------
    aes70_hosts = _parse_host_list(settings.get(const.CONF_AES70_HOSTS))
    if aes70_hosts:
        aes70_kwargs: dict[str, Any] = {}
        configured_port = settings.get(const.CONF_AES70_PORT)
        if configured_port:
            aes70_kwargs["port"] = int(configured_port)
        aes70_monitor = AES70Monitor(aes70_hosts, **aes70_kwargs)
        if await _try_start("aes70_monitor", aes70_monitor, resources):
            coordinator.aes70_monitor = aes70_monitor

    # -- AVDECC/Milan (external LA_avdecc bridge; explicit URL required) -----------
    avdecc_url = settings.get(const.CONF_AVDECC_BRIDGE_URL)
    if avdecc_url:
        avdecc_monitor = AVDECCBridgeMonitor(avdecc_url)
        if await _try_start("avdecc_monitor", avdecc_monitor, resources):
            coordinator.avdecc_monitor = avdecc_monitor

    # -- RDM / RDMnet (external HTTP bridges; explicit URL required) ---------------
    if settings.get(const.CONF_RDM_ENABLED) and settings.get(const.CONF_RDM_BRIDGE_URL):
        rdm_bridge = RDMBridgeMonitor(settings[const.CONF_RDM_BRIDGE_URL], transport="RDM/OLA")
        if await _try_start("rdm_bridge", rdm_bridge, resources):
            coordinator.rdm_bridge = rdm_bridge
    if settings.get(const.CONF_RDMNET_ENABLED) and settings.get(const.CONF_RDMNET_BRIDGE_URL):
        rdmnet_bridge = RDMBridgeMonitor(settings[const.CONF_RDMNET_BRIDGE_URL], transport="RDMnet")
        if await _try_start("rdmnet_bridge", rdmnet_bridge, resources):
            coordinator.rdmnet_bridge = rdmnet_bridge

    # -- grandMA3 / MA-Net3 ---------------------------------------------------------
    if settings.get(const.CONF_MA_ENABLED):
        ma_listener = MANet3Listener(settings.get(const.CONF_INTERFACE_MA, default_interface))
        if await _try_start("ma_listener", ma_listener, resources):
            coordinator.ma_listener = ma_listener

    # -- OSC input --------------------------------------------------------------------
    if settings.get(const.CONF_OSC_INPUT_ENABLED):
        # NOTE (audit finding): coordinator.py has no method that turns an
        # incoming OSCMessage into an HA action -- control_mapping.py and
        # osc_mapping.py exist and implement a MappingEngine for exactly
        # this, but neither is imported anywhere in coordinator.py. Until
        # that gap is closed, incoming OSC still reaches OSC Learn mode
        # (genuinely useful on its own -- it captures addresses/values for
        # the UI to suggest mappings from) but does not yet trigger any
        # action by itself. callback=None reflects that honestly instead of
        # pointing at a method that does not exist.
        osc_receiver = OSCReceiver(
            host=settings.get(const.CONF_OSC_INPUT_INTERFACE, default_interface),
            port=int(settings.get(const.CONF_OSC_INPUT_PORT, const.OSC_PORT)),
            learn=coordinator.osc_learn,
            callback=None,
        )
        if await _try_start("osc_receiver", osc_receiver, resources):
            coordinator.osc_receiver = osc_receiver

    # -- MIDI input -------------------------------------------------------------------
    if settings.get(const.CONF_MIDI_ENABLED) and settings.get(const.CONF_MIDI_DEVICE):
        # Same honest gap as OSC above: no coordinator method consumes
        # normalized MIDIMessage objects yet. A no-op callback keeps the
        # input running (useful for a future Learn-mode-style feature)
        # without pretending an action pipeline exists.
        midi_input = MIDIInputRuntime(settings[const.CONF_MIDI_DEVICE], lambda message: None)
        started = await midi_input.async_start()
        if started:
            coordinator.midi_input = midi_input
            resources.register("midi_input", midi_input, stop_method="async_stop")
        else:
            _LOGGER.warning("Could not start MIDI input on %s: %s", settings[const.CONF_MIDI_DEVICE], midi_input.error)

    # -- PunchLight (RTP-MIDI DLi-LAN) -------------------------------------------------
    if settings.get(const.CONF_PUNCHLIGHT_ENABLED) and settings.get(const.CONF_PUNCHLIGHT_DEVICE):
        async def _on_punchlight_change(snapshot: dict) -> None:
            coordinator.publish(punchlight=snapshot)

        punchlight = PunchLightState(settings[const.CONF_PUNCHLIGHT_DEVICE], _on_punchlight_change)
        started = await punchlight.async_start()
        if started:
            coordinator.punchlight = punchlight
            resources.register("punchlight", punchlight, stop_method="async_stop")
        else:
            _LOGGER.warning("Could not start PunchLight on %s: %s", settings[const.CONF_PUNCHLIGHT_DEVICE], punchlight.last_error)

    # -- ETC Sensor3/CEM3 ---------------------------------------------------------------
    if settings.get(const.CONF_ETC_CEM3_ENABLED):
        cem3_hosts = _parse_host_list(settings.get(const.CONF_ETC_CEM3_HOSTS))
        coordinator.etc_cem3_monitor = CEM3WebMonitor(
            cem3_hosts,
            source_ips=_parse_host_list(settings.get(const.CONF_ETC_CEM3_INTERFACES)) or None,
            discovery=bool(settings.get(const.CONF_ETC_CEM3_DISCOVERY, False)),
        )
        # CEM3WebMonitor is polled from coordinator's own refresh cycle
        # (async_update()), so nothing to start/register as a background task here.

    # -- SMPTE ST 2110 --------------------------------------------------------------------
    st2110_monitor = ST2110PassiveInspector(interface=settings.get(const.CONF_VIDEO_IP_INTERFACE, default_interface))
    if await _try_start("st2110_monitor", st2110_monitor, resources):
        coordinator.st2110_monitor = st2110_monitor

    # -- Video IP supervision (NDI mDNS + folds in ST 2110 SDP discovery) ----------------
    if settings.get(const.CONF_VIDEO_IP_ENABLED, True):
        try:
            await coordinator.video_ip_supervision.async_scan_ndi(hass)
        except Exception as exc:
            _LOGGER.debug("Initial NDI scan failed (will retry on next refresh): %s", exc)

    # -- Projector control gate ------------------------------------------------------------
    coordinator.projector_monitor_enabled = bool(settings.get(const.CONF_PROJECTOR_MONITOR_ENABLED, True))
    # NOTE: the "projectors" JSON list from config_flow.py (per-host vendor
    # profile + credentials) is intentionally not applied here yet -- see
    # module docstring. coordinator.projector_monitor keeps relying on
    # PJLink broadcast auto-discovery in the meantime, which needs no wiring.

    # -- Signal watchdog (single configured rule; UI currently exposes one) -------------
    if settings.get(const.CONF_WATCHDOG_ENABLED):
        loss_scene = settings.get(const.CONF_WATCHDOG_LOSS_SCENE)
        recovery_scene = settings.get(const.CONF_WATCHDOG_RECOVERY_SCENE)
        coordinator.watchdogs.add(WatchdogRule(
            name="configured_watchdog",
            protocol=settings.get(const.CONF_WATCHDOG_PROTOCOL, "*"),
            universe=int(settings.get(const.CONF_WATCHDOG_UNIVERSE, 1)),
            source=settings.get(const.CONF_WATCHDOG_SOURCE) or None,
            timeout_s=float(settings.get(const.CONF_WATCHDOG_TIMEOUT, 10.0)),
            action_lost={"domain": "scene", "service": "turn_on", "entity_id": loss_scene} if loss_scene else None,
            action_restored={"domain": "scene", "service": "turn_on", "entity_id": recovery_scene} if recovery_scene else None,
        ))
    coordinator.watchdogs.start()

    # -- Rules: load persisted rules into the already-constructed RuleSet ---------------
    coordinator.rules.set_rules(await coordinator.rule_store.async_load())

    # -- Capacity config (static estimates the operator provides) -----------------------
    coordinator.capacity_config = {
        "link_mbps": float(settings.get(const.CONF_CAPACITY_LINK_MBPS, 1000.0)),
        "dante_mbps": float(settings.get(const.CONF_CAPACITY_DANTE_MBPS, 0.0)),
        "cameras_mbps": float(settings.get(const.CONF_CAPACITY_CAMERAS_MBPS, 0.0)),
        "st2110_mbps": float(settings.get(const.CONF_CAPACITY_ST2110_MBPS, 0.0)),
        "other_mbps": float(settings.get(const.CONF_CAPACITY_OTHER_MBPS, 0.0)),
    }

    coordinator.async_start_workers()

    values: dict[str, Any] = {
        "coordinator": coordinator,
        "resource_registry": resources,
        "archive": archive,
        "backup_manager": coordinator.config_backups,
        "ma_listener": getattr(coordinator, "ma_listener", None),
        "ptp_monitor": coordinator.ptp_monitor,
        "dante_monitor": coordinator.dante_monitor,
        "aes67_monitor": coordinator.aes67_monitor,
        "enttec_input": getattr(coordinator, "enttec_input", None),
        "dmx_network": coordinator.dmx_network,
        "punchlight": getattr(coordinator, "punchlight", None),
    }

    return Runtime(coordinator=coordinator, resources=resources, archive=archive, backup_manager=coordinator.config_backups, values=values)
