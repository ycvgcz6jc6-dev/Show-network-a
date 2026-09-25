from __future__ import annotations

import asyncio
import json
import socket
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import const
from .enttec import discover_ports
from .midi_runtime import MIDIInputRuntime
from .network_interfaces import snapshot as network_interface_snapshot


def _interfaces(rows: list[dict] | None = None) -> list[str]:
    values = ["0.0.0.0"]
    for row in rows or []:
        for address in row.get("addresses", []):
            if address and ":" not in address and address not in values:
                values.append(address)
    return values


def _notification_choices(hass, current: str = "") -> list[str]:
    choices = ["persistent"]
    for service in hass.services.async_services().get("notify", {}):
        value = f"notify.{service}"
        if value not in choices:
            choices.append(value)
    if current and current not in choices:
        choices.append(current)
    return choices


def _field_format_errors(data: dict) -> dict[str, str]:
    """Validate the handful of fields that need more than a bare string,
    returning {field: error_key} the same way _osc_port_conflict_error
    already does -- checked *after* form submission, in async_step_user/
    async_step_init, never embedded in the schema itself.

    AUDIT FIX: these were previously vol.All(str, <custom function>)
    schema validators. Home Assistant's own frontend needs to serialize
    the schema to JSON to render the form at all, and a bare Python
    function has no serializable representation -- confirmed directly
    in production: "ValueError: unable to serialize schema: <function
    _optional_pdu_hosts ...>", which crashed the *entire* config/options
    flow with a 500 error the instant it tried to open, for every field,
    not just the offending one. Schema fields are back to plain `str`;
    all the same validation semantics are kept here, just checked after
    submission instead of during rendering -- the same architecture this
    project's own OSC port conflict check already used correctly.
    """
    errors: dict[str, str] = {}

    for key in (const.CONF_AVDECC_BRIDGE_URL, const.CONF_RDM_BRIDGE_URL, const.CONF_RDMNET_BRIDGE_URL):
        text = str(data.get(key) or "").strip()
        if not text:
            continue
        try:
            validated = vol.Url()(text)
            from urllib.parse import urlparse
            if urlparse(validated).scheme not in ("http", "https"):
                raise vol.Invalid("scheme")
        except vol.Invalid:
            errors[key] = "invalid_bridge_url"

    group = str(data.get(const.CONF_GREENGO_MULTICAST_GROUP) or "").strip()
    if group:
        import ipaddress
        try:
            addr = ipaddress.IPv4Address(group)
            if not addr.is_multicast:
                raise ValueError
        except ValueError:
            errors[const.CONF_GREENGO_MULTICAST_GROUP] = "invalid_multicast_group"

    ping_target = str(data.get(const.CONF_MILLUMIN_PING_TARGET) or "").strip()
    if ping_target:
        valid = False
        if ":" in ping_target:
            host, _, port_text = ping_target.rpartition(":")
            if host and port_text.isdigit() and 1 <= int(port_text) <= 65535:
                valid = True
        if not valid:
            errors[const.CONF_MILLUMIN_PING_TARGET] = "invalid_host_port"

    pdu_hosts = str(data.get(const.CONF_PDU_HOSTS) or "").strip()
    if pdu_hosts:
        from .pdu_monitor import SUPPORTED_VENDORS
        for part in pdu_hosts.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            _host, _, vendor = part.rpartition(":")
            if ":" not in part or vendor not in SUPPORTED_VENDORS:
                errors[const.CONF_PDU_HOSTS] = "invalid_pdu_hosts"
                break

    return errors


def _udp_port_available(host: str, port: int) -> bool:
    """Best-effort check: can a UDP socket bind to (host, port) right now?

    Not a guarantee (another process could grab the port between this check
    and the real integration startup), but it catches the common case --
    the exact scenario an audit found in production, where OSC silently
    failed to start because port 8000 was already taken by something else
    -- at configuration time instead of only in the log afterwards.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host or "0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


async def _osc_port_conflict_error(hass, data: dict, *, previous_port: int | None = None) -> dict[str, str]:
    """Return {"osc_input_port": "port_in_use"} if OSC is enabled and its
    configured port cannot be bound right now, else an empty dict.

    ``previous_port``: when editing an existing entry's options, pass the
    port that entry is *currently* running with. If the submitted port is
    unchanged, the bind check is skipped entirely -- the running OSC
    receiver already legitimately holds that port itself, so re-saving
    unchanged options must never be blocked by a false-positive conflict
    against the entry's own listener.
    """
    if not data.get(const.CONF_OSC_INPUT_ENABLED):
        return {}
    host = str(data.get(const.CONF_OSC_INPUT_INTERFACE) or "0.0.0.0")
    try:
        port = int(data.get(const.CONF_OSC_INPUT_PORT, 8000))
    except (TypeError, ValueError):
        return {}
    if previous_port is not None and port == previous_port:
        return {}
    available = await hass.async_add_executor_job(_udp_port_available, host, port)
    return {} if available else {"osc_input_port": "port_in_use"}


async def _choices_for_hass(hass, *, timeout: float = 5.0) -> tuple[list[str], list[str], list[str]]:
    """Discover form choices without blocking Home Assistant's event loop.

    Each source is bounded individually (audit: a stuck ENTTEC USB or MIDI
    port enumeration on some systems could otherwise hang this indefinitely
    -- nothing here previously had any timeout at all, so the config/options
    menu itself would simply never open, matching a real report of
    "j'arrive plus à accéder au menu configuration". Falls back to an empty
    list for whichever source timed out rather than failing the whole menu,
    the same "don't let one slow thing starve everything else" fix already
    applied to ResourceRegistry.async_stop_all. `timeout` is a parameter
    (not a hardcoded constant) purely so tests can exercise a real timeout
    without waiting for the production default.
    """
    async def _bounded(coro):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except (asyncio.TimeoutError, Exception):
            return []

    rows, enttec_ports, midi_ports = await asyncio.gather(
        _bounded(hass.async_add_executor_job(network_interface_snapshot)),
        _bounded(hass.async_add_executor_job(discover_ports)),
        _bounded(hass.async_add_executor_job(MIDIInputRuntime.list_input_ports)),
    )
    return _interfaces(rows), [port.device for port in enttec_ports], midi_ports


def _schema_for_hass(hass, data: dict | None, interfaces: list[str], enttec_ports: list[str], midi_ports: list[str]):
    data = data or {}
    interface = data.get(const.CONF_INTERFACE, "0.0.0.0")
    interface_fields = {
        const.CONF_INTERFACE: vol.Required(const.CONF_INTERFACE, default=interface),
        const.CONF_INTERFACE_DMX: vol.Optional(const.CONF_INTERFACE_DMX, default=data.get(const.CONF_INTERFACE_DMX, interface)),
        const.CONF_INTERFACE_DANTE: vol.Optional(const.CONF_INTERFACE_DANTE, default=data.get(const.CONF_INTERFACE_DANTE, interface)),
        const.CONF_INTERFACE_PTP: vol.Optional(const.CONF_INTERFACE_PTP, default=data.get(const.CONF_INTERFACE_PTP, interface)),
        const.CONF_INTERFACE_MA: vol.Optional(const.CONF_INTERFACE_MA, default=data.get(const.CONF_INTERFACE_MA, interface)),
        const.CONF_INTERFACE_AUDIO: vol.Optional(const.CONF_INTERFACE_AUDIO, default=data.get(const.CONF_INTERFACE_AUDIO, interface)),
        const.CONF_OSC_INPUT_INTERFACE: vol.Optional(const.CONF_OSC_INPUT_INTERFACE, default=data.get(const.CONF_OSC_INPUT_INTERFACE, interface)),
        const.CONF_VIDEO_IP_INTERFACE: vol.Optional(const.CONF_VIDEO_IP_INTERFACE, default=data.get(const.CONF_VIDEO_IP_INTERFACE, interface)),
        const.CONF_INTERFACE_ETC: vol.Optional(const.CONF_INTERFACE_ETC, default=data.get(const.CONF_INTERFACE_ETC, interface)),
        const.CONF_TALLY_IP_INTERFACE: vol.Optional(const.CONF_TALLY_IP_INTERFACE, default=data.get(const.CONF_TALLY_IP_INTERFACE, interface)),
    }
    schema = {key: vol.In(interfaces) for key in interface_fields.values()}
    schema.update({
        vol.Optional(const.CONF_DMX_ARTNET_ENABLED, default=data.get(const.CONF_DMX_ARTNET_ENABLED, True)): bool,
        vol.Optional(const.CONF_DMX_SACN_ENABLED, default=data.get(const.CONF_DMX_SACN_ENABLED, True)): bool,
        vol.Optional(const.CONF_DMX_SOURCE, default=data.get(const.CONF_DMX_SOURCE, "")): str,
        vol.Required(const.CONF_UNIVERSES, default=data.get(const.CONF_UNIVERSES, "1-16")): str,
        vol.Optional(const.CONF_MA_ENABLED, default=data.get(const.CONF_MA_ENABLED, True)): bool,
        vol.Required(const.CONF_THRESHOLD, default=data.get(const.CONF_THRESHOLD, 10)): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Required(const.CONF_LANGUAGE, default=data.get(const.CONF_LANGUAGE, "auto")): vol.In(["auto", "fr", "en", "es", "it", "nl", "de"]),
        vol.Optional(const.CONF_PERFORMANCE_PROFILE, default=data.get(const.CONF_PERFORMANCE_PROFILE, "auto")): vol.In(const.PERFORMANCE_PROFILES),
        vol.Optional(const.CONF_GIGACORE_HOSTS, default=data.get(const.CONF_GIGACORE_HOSTS, "")): str,
        vol.Optional(const.CONF_GENERIC_SWITCH_HOSTS, default=data.get(const.CONF_GENERIC_SWITCH_HOSTS, "")): str,
        vol.Optional(const.CONF_UPS_HOSTS, default=data.get(const.CONF_UPS_HOSTS, "")): str,
        vol.Optional(const.CONF_GIGACORE_COMMUNITY, default=data.get(const.CONF_GIGACORE_COMMUNITY, const.DEFAULT_GIGACORE_COMMUNITY)): str,
        vol.Optional(const.CONF_AES70_HOSTS, default=data.get(const.CONF_AES70_HOSTS, "")): str,
        vol.Optional(const.CONF_YAMAHA_OSC_HOSTS, default=data.get(const.CONF_YAMAHA_OSC_HOSTS, "")): str,
        vol.Optional(const.CONF_QLAB_HOSTS, default=data.get(const.CONF_QLAB_HOSTS, "")): str,
        vol.Optional(const.CONF_RESOLUME_HOSTS, default=data.get(const.CONF_RESOLUME_HOSTS, "")): str,
        vol.Optional(const.CONF_NEXUS_AUDIO_HOSTS, default=data.get(const.CONF_NEXUS_AUDIO_HOSTS, "")): str,
        vol.Optional(const.CONF_PDU_HOSTS, default=data.get(const.CONF_PDU_HOSTS, "")): str,
        vol.Optional(const.CONF_REOLINK_HA_ENABLED, default=data.get(const.CONF_REOLINK_HA_ENABLED, False)): bool,
        vol.Optional(const.CONF_NEXUS_AUDIO_PLAYERS, default=data.get(const.CONF_NEXUS_AUDIO_PLAYERS, "")): str,
        vol.Optional(const.CONF_MILLUMIN_LISTEN_PORT, default=data.get(const.CONF_MILLUMIN_LISTEN_PORT, 0)): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        vol.Optional(const.CONF_MILLUMIN_PING_TARGET, default=data.get(const.CONF_MILLUMIN_PING_TARGET, "")): str,
        vol.Optional(const.CONF_SENDSPIN_DANTE_PLAYERS, default=data.get(const.CONF_SENDSPIN_DANTE_PLAYERS, "")): str,
        vol.Optional(const.CONF_GREENGO_MULTICAST_GROUP, default=data.get(const.CONF_GREENGO_MULTICAST_GROUP, "")): str,
        vol.Optional(const.CONF_AES70_PORT, default=data.get(const.CONF_AES70_PORT, 65000)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(const.CONF_AVDECC_BRIDGE_URL, default=data.get(const.CONF_AVDECC_BRIDGE_URL, "")): str,
        vol.Optional(const.CONF_AVDECC_BRIDGE_TOKEN, default=data.get(const.CONF_AVDECC_BRIDGE_TOKEN, "")): str,
        vol.Optional(const.CONF_RDM_ENABLED, default=data.get(const.CONF_RDM_ENABLED, False)): bool,
        vol.Optional(const.CONF_RDM_BRIDGE_URL, default=data.get(const.CONF_RDM_BRIDGE_URL, "")): str,
        vol.Optional(const.CONF_RDM_BRIDGE_TOKEN, default=data.get(const.CONF_RDM_BRIDGE_TOKEN, "")): str,
        vol.Optional(const.CONF_RDMNET_ENABLED, default=data.get(const.CONF_RDMNET_ENABLED, False)): bool,
        vol.Optional(const.CONF_RDMNET_BRIDGE_URL, default=data.get(const.CONF_RDMNET_BRIDGE_URL, "")): str,
        vol.Optional(const.CONF_RDMNET_BRIDGE_TOKEN, default=data.get(const.CONF_RDMNET_BRIDGE_TOKEN, "")): str,
        vol.Optional(const.CONF_RDM_ALLOW_WRITES, default=data.get(const.CONF_RDM_ALLOW_WRITES, False)): bool,
        vol.Optional(const.CONF_ENTTEC_DEVICE, default=data.get(const.CONF_ENTTEC_DEVICE, "")): vol.In([""] + enttec_ports),
        vol.Optional(const.CONF_ENTTEC_MODEL, default=data.get(const.CONF_ENTTEC_MODEL, "auto")): vol.In(["auto", "DMX USB Pro", "DMX USB Pro Mk2"]),
        vol.Optional(const.CONF_OSC_INPUT_ENABLED, default=data.get(const.CONF_OSC_INPUT_ENABLED, False)): bool,
        vol.Optional(const.CONF_OSC_INPUT_PORT, default=data.get(const.CONF_OSC_INPUT_PORT, 8000)): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
        vol.Optional(const.CONF_MIDI_ENABLED, default=data.get(const.CONF_MIDI_ENABLED, False)): bool,
        vol.Optional(const.CONF_MIDI_DEVICE, default=data.get(const.CONF_MIDI_DEVICE, "")): vol.In([""] + midi_ports),
        vol.Optional(const.CONF_PUNCHLIGHT_ENABLED, default=data.get(const.CONF_PUNCHLIGHT_ENABLED, False)): bool,
        vol.Optional(const.CONF_PUNCHLIGHT_DEVICE, default=data.get(const.CONF_PUNCHLIGHT_DEVICE, "")): vol.In([""] + midi_ports),
        vol.Optional(const.CONF_TALLY_IP_ENABLED, default=data.get(const.CONF_TALLY_IP_ENABLED, False)): bool,
        vol.Optional(const.CONF_TALLY_IP_PORT, default=data.get(const.CONF_TALLY_IP_PORT, const.DEFAULT_TALLY_IP_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(const.CONF_TALLY_IP_SCREEN, default=data.get(const.CONF_TALLY_IP_SCREEN, -1)): vol.All(vol.Coerce(int), vol.Range(min=-1, max=65535)),
        vol.Optional(const.CONF_TALLY_IP_INDEX, default=data.get(const.CONF_TALLY_IP_INDEX, -1)): vol.All(vol.Coerce(int), vol.Range(min=-1, max=65535)),
        vol.Optional(const.CONF_TALLY_IP_STALE_TIMEOUT, default=data.get(const.CONF_TALLY_IP_STALE_TIMEOUT, 10.0)): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=3600)),
        vol.Optional(const.CONF_WATCHDOG_ENABLED, default=data.get(const.CONF_WATCHDOG_ENABLED, False)): bool,
        vol.Optional(const.CONF_WATCHDOG_PROTOCOL, default=data.get(const.CONF_WATCHDOG_PROTOCOL, "ENTTEC")): vol.In(["ENTTEC", "sACN", "Art-Net"]),
        vol.Optional(const.CONF_WATCHDOG_UNIVERSE, default=data.get(const.CONF_WATCHDOG_UNIVERSE, 1)): vol.All(vol.Coerce(int), vol.Range(min=1, max=63999)),
        vol.Optional(const.CONF_WATCHDOG_TIMEOUT, default=data.get(const.CONF_WATCHDOG_TIMEOUT, 10)): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=3600)),
        vol.Optional(const.CONF_WATCHDOG_RECOVERY_DELAY, default=data.get(const.CONF_WATCHDOG_RECOVERY_DELAY, 3)): vol.All(vol.Coerce(float), vol.Range(min=0, max=3600)),
        vol.Optional("switch_manufacturers", default=data.get("switch_manufacturers", ["luminex", "elc", "green_go"])): selector.SelectSelector(selector.SelectSelectorConfig(options=["luminex", "elc", "green_go"], multiple=True)),
        vol.Optional(const.CONF_ARCHIVE_DESTINATION, default=data.get(const.CONF_ARCHIVE_DESTINATION, "show_network_archive")): str,
        vol.Optional(const.CONF_NOTIFICATION_ENABLED, default=data.get(const.CONF_NOTIFICATION_ENABLED, False)): bool,
        vol.Optional(const.CONF_NOTIFICATION_TARGET, default=data.get(const.CONF_NOTIFICATION_TARGET, "persistent")): vol.In(_notification_choices(hass, data.get(const.CONF_NOTIFICATION_TARGET, ""))),
        vol.Optional(const.CONF_NOTIFICATION_MODE, default=data.get(const.CONF_NOTIFICATION_MODE, "both")): vol.In(["notify", "persistent", "both"]),
        vol.Optional(const.CONF_HA_BUILDER_ENABLED, default=data.get(const.CONF_HA_BUILDER_ENABLED, True)): bool,
        vol.Optional(const.CONF_PROJECTOR_MONITOR_ENABLED, default=data.get(const.CONF_PROJECTOR_MONITOR_ENABLED, True)): bool,
        vol.Optional(const.CONF_ETC_CEM3_ENABLED, default=data.get(const.CONF_ETC_CEM3_ENABLED, False)): bool,
        vol.Optional(const.CONF_ONTIME_ENABLED, default=data.get(const.CONF_ONTIME_ENABLED, False)): bool,
        vol.Optional(const.CONF_ONTIME_HOST, default=data.get(const.CONF_ONTIME_HOST, "")): str,
        vol.Optional(const.CONF_ONTIME_PORT, default=data.get(const.CONF_ONTIME_PORT, 4001)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(const.CONF_QLCPLUS_ENABLED, default=data.get(const.CONF_QLCPLUS_ENABLED, False)): bool,
        vol.Optional(const.CONF_QLCPLUS_HOST, default=data.get(const.CONF_QLCPLUS_HOST, "")): str,
        vol.Optional(const.CONF_QLCPLUS_PORT, default=data.get(const.CONF_QLCPLUS_PORT, 9999)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(const.CONF_ETC_CEM3_HOSTS, default=data.get(const.CONF_ETC_CEM3_HOSTS, "")): str,
        vol.Optional(const.CONF_ETC_CEM3_DISCOVERY, default=data.get(const.CONF_ETC_CEM3_DISCOVERY, False)): bool,
        vol.Optional(const.CONF_ETC_CEM3_INTERFACES, default=data.get(const.CONF_ETC_CEM3_INTERFACES, [])): selector.SelectSelector(selector.SelectSelectorConfig(options=[ip for ip in interfaces if ip != "0.0.0.0"], multiple=True)),
        vol.Optional(const.CONF_VIDEO_IP_ENABLED, default=data.get(const.CONF_VIDEO_IP_ENABLED, True)): bool,
        vol.Optional(const.CONF_VIDEO_IP_PREVIEW_ENABLED, default=data.get(const.CONF_VIDEO_IP_PREVIEW_ENABLED, False)): bool,
        vol.Optional(const.CONF_CHAOS_ENABLED, default=data.get(const.CONF_CHAOS_ENABLED, False)): bool,
        vol.Optional(const.CONF_ARCHIVE_RETENTION_DAYS, default=data.get(const.CONF_ARCHIVE_RETENTION_DAYS, 30)): vol.All(vol.Coerce(int), vol.Range(min=1, max=3650)),
        vol.Optional(const.CONF_ARCHIVE_MAX_BYTES, default=data.get(const.CONF_ARCHIVE_MAX_BYTES, 5 * 1024 * 1024)): vol.All(vol.Coerce(int), vol.Range(min=256000, max=100 * 1024 * 1024)),
        vol.Optional(const.CONF_CAPACITY_LINK_MBPS, default=data.get(const.CONF_CAPACITY_LINK_MBPS, 1000)): vol.All(vol.Coerce(float), vol.Range(min=10, max=100000)),
        vol.Optional(const.CONF_CAPACITY_DANTE_MBPS, default=data.get(const.CONF_CAPACITY_DANTE_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
        vol.Optional(const.CONF_DANTE_MANAGED_URL, default=data.get(const.CONF_DANTE_MANAGED_URL, "")): str,
        vol.Optional(const.CONF_DANTE_MANAGED_API_KEY, default=data.get(const.CONF_DANTE_MANAGED_API_KEY, "")): str,
        vol.Optional(const.CONF_DANTE_MANAGED_DOMAIN_ID, default=data.get(const.CONF_DANTE_MANAGED_DOMAIN_ID, "")): str,
        vol.Optional(const.CONF_CAPACITY_CAMERAS_MBPS, default=data.get(const.CONF_CAPACITY_CAMERAS_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
        vol.Optional(const.CONF_CAPACITY_ST2110_MBPS, default=data.get(const.CONF_CAPACITY_ST2110_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
        vol.Optional(const.CONF_CAPACITY_OTHER_MBPS, default=data.get(const.CONF_CAPACITY_OTHER_MBPS, 0)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
        vol.Optional("projectors", default=json.dumps(data.get("projectors", [])) if isinstance(data.get("projectors", []), list) else data.get("projectors", "")): str,
    })
    return vol.Schema(schema)


class DmxMonitorConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
    VERSION = 2

    async def _choices(self):
        return await _choices_for_hass(self.hass)

    def _schema(self, data: dict | None, interfaces: list[str], enttec_ports: list[str], midi_ports: list[str]):
        return _schema_for_hass(self.hass, data, interfaces, enttec_ports, midi_ports)

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("show_network")
        self._abort_if_unique_id_configured()
        interfaces, enttec_ports, midi_ports = await self._choices()
        if user_input is not None:
            data = dict(user_input)
            try:
                data["projectors"] = json.loads(data.get("projectors") or "[]")
                if not isinstance(data["projectors"], list):
                    raise ValueError
            except (TypeError, ValueError, json.JSONDecodeError):
                return self.async_show_form(step_id="user", data_schema=self._schema(data, interfaces, enttec_ports, midi_ports), errors={"projectors": "invalid_json"})
            osc_errors = await _osc_port_conflict_error(self.hass, data)
            field_errors = _field_format_errors(data)
            errors = {**osc_errors, **field_errors}
            if errors:
                return self.async_show_form(step_id="user", data_schema=self._schema(data, interfaces, enttec_ports, midi_ports), errors=errors)
            return self.async_create_entry(title="Show Network", data=data)
        return self.async_show_form(step_id="user", data_schema=self._schema({}, interfaces, enttec_ports, midi_ports))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        # Home Assistant exposes the entry through OptionsFlow.config_entry.
        return DmxMonitorOptionsFlow()


class DmxMonitorOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        interfaces, enttec_ports, midi_ports = await _choices_for_hass(self.hass)
        if user_input is not None:
            data = dict(user_input)
            try:
                data["projectors"] = json.loads(data.get("projectors") or "[]")
                if not isinstance(data["projectors"], list):
                    raise ValueError
            except (TypeError, ValueError, json.JSONDecodeError):
                return self.async_show_form(step_id="init", data_schema=_schema_for_hass(self.hass, data, interfaces, enttec_ports, midi_ports), errors={"projectors": "invalid_json"})
            osc_errors = await _osc_port_conflict_error(
                self.hass, data,
                previous_port=int({**self.config_entry.data, **self.config_entry.options}.get(const.CONF_OSC_INPUT_PORT, 8000)),
            )
            field_errors = _field_format_errors(data)
            errors = {**osc_errors, **field_errors}
            if errors:
                return self.async_show_form(step_id="init", data_schema=_schema_for_hass(self.hass, data, interfaces, enttec_ports, midi_ports), errors=errors)
            return self.async_create_entry(data=data)
        data = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema_for_hass(self.hass, data, interfaces, enttec_ports, midi_ports))
