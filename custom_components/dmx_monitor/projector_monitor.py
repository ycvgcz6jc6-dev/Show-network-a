from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict, field
from typing import Any

from .projector_protocols import (
    BarcoPulseJSONRPC,
    ChristieHSSerialAPI,
    DigitalProjectionASCII,
    PJLinkClient,
    PanasonicWebAPI,
    ProjectorAuthError,
    ProjectorTelemetry,
)

_ERROR_NAMES = ("fan", "lamp", "temperature", "cover", "filter", "other")
_ERROR_LEVEL = {"0": "ok", "1": "warning", "2": "error"}

# NOTE: isolated from Home Assistant's shared default executor for the same
# reason as snmp.py's _SNMP_EXECUTOR -- projector discovery/polling is real
# network I/O with unpredictable latency (a slow or unreachable projector
# ties up a worker for its full timeout), and with several such projectors
# this could otherwise starve the shared pool of workers for unrelated core
# Home Assistant operations.
_PROJECTOR_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="show_network_projector")


@dataclass
class ProjectorRecord:
    name: str
    host: str
    port: int = 4352
    manufacturer: str | None = None
    model: str | None = None
    pjlink_class: str | None = None
    serial_number: str | None = None
    software_version: str | None = None
    other_info: str | None = None
    power: str | None = None
    input_source: str | None = None
    input_name: str | None = None
    available_inputs: list[str] = field(default_factory=list)
    av_mute: str | None = None
    errors: str | None = None
    error_detail: dict[str, Any] = field(default_factory=dict)
    lamp_hours: int | None = None
    lamp_status: str | None = None
    filter_hours: int | None = None
    lamp_replacement: str | None = None
    filter_replacement: str | None = None
    input_resolution: str | None = None
    recommended_resolution: str | None = None
    temperatures_c: dict[str, float] = field(default_factory=dict)
    temperature_c: float | None = None
    fans_rpm: dict[str, float] = field(default_factory=dict)
    source_hours: dict[str, float] = field(default_factory=dict)
    signal: str | None = None
    transport: str | None = None
    telemetry_source: str | None = None
    authenticated: bool | None = None
    auth_method: str | None = None
    capabilities: list[str] = field(default_factory=list)
    profile: str = "auto"
    online: bool = False
    reachable: bool = False
    valid_telemetry: bool = False
    stale: bool = True
    discovered: bool = False
    mac: str | None = None
    last_error: str | None = None
    last_seen_monotonic: float | None = None
    last_success_monotonic: float | None = None
    age_s: float | None = None
    telemetry_age_s: float | None = None
    source_interface: str | None = None


class PJLinkMonitor:
    """Multi-protocol projector monitor.

    PJLink remains the standards-based discovery/fallback transport. Explicitly
    configured vendor profiles may add read-only telemetry from the documented
    Panasonic Web API, Digital Projection ASCII family, Christie HS serial API,
    or Barco Pulse JSON-RPC API. No vendor protocol is inferred only from an IP.
    """

    def __init__(self, projectors: list[dict[str, Any]] | None = None):
        self.records: list[ProjectorRecord] = []
        self._by_host: dict[str, ProjectorRecord] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self.last_discovery_monotonic: float | None = None
        self.discovery_errors: list[str] = []
        for p in projectors or []:
            if p.get("host"):
                host = str(p["host"])
                self._configs[host] = dict(p)
                self._ensure_record(
                    host=host,
                    port=int(p.get("port", 4352)),
                    name=str(p.get("name") or host),
                    profile=str(p.get("profile", "auto")),
                    discovered=False,
                    mac=p.get("mac"),
                )

    def config_for(self, host: str) -> dict[str, Any]:
        return dict(self._configs.get(host, {}))

    def get_record(self, host: str) -> ProjectorRecord | None:
        return self._by_host.get(host)

    def _ensure_record(self, *, host: str, port: int = 4352, name: str | None = None,
                       profile: str = "auto", discovered: bool = False,
                       mac: str | None = None, source_interface: str | None = None) -> ProjectorRecord:
        rec = self._by_host.get(host)
        if rec is None:
            rec = ProjectorRecord(name=name or host, host=host, port=port, profile=profile,
                                  discovered=discovered, mac=mac, source_interface=source_interface)
            self._by_host[host] = rec
            self.records.append(rec)
        else:
            rec.port = port or rec.port
            rec.discovered = rec.discovered or discovered
            rec.mac = mac or rec.mac
            rec.source_interface = source_interface or rec.source_interface
            if profile and rec.profile == "auto":
                rec.profile = profile
            if name and rec.name == rec.host:
                rec.name = name
        return rec

    @staticmethod
    def _payload(value: str | None) -> str | None:
        return PJLinkClient.value(value or "")

    @staticmethod
    def _normalize_profile(profile: str) -> str:
        return str(profile or "auto").strip().lower().replace("-", "_").replace(" ", "_")

    def _adapter_for(self, r: ProjectorRecord):
        cfg = self._configs.get(r.host, {})
        profile = self._normalize_profile(cfg.get("profile", r.profile))
        timeout = float(cfg.get("timeout", 2.0))
        if profile in {"panasonic_webapi", "panasonic_web_api", "panasonic"}:
            return PanasonicWebAPI(
                r.host,
                username=cfg.get("username"), password=cfg.get("password"),
                scheme=str(cfg.get("scheme", "http")),
                port=int(cfg["vendor_port"]) if cfg.get("vendor_port") else None,
                timeout=timeout,
            )
        if profile in {
            "digital_projection_ascii", "digital_projection_rev_a", "digital_projection_rev_f",
            "digital_projection_rev_h", "digital_projection_simplified",
        }:
            return DigitalProjectionASCII(r.host, int(cfg.get("vendor_port", 7000)), timeout=timeout)
        if profile in {"christie_hs", "christie_hs_2k", "christie_hs_serial"}:
            return ChristieHSSerialAPI(r.host, int(cfg.get("vendor_port", 3002)), timeout=timeout)
        if profile in {"barco_pulse", "barco_prospector", "barco_jsonrpc"}:
            passcode = cfg.get("passcode")
            return BarcoPulseJSONRPC(
                r.host, int(cfg.get("vendor_port", 9090)), timeout=timeout,
                passcode=int(passcode) if passcode not in (None, "") else None,
            )
        return None

    def _pjlink_client_for(self, r: ProjectorRecord) -> PJLinkClient:
        cfg = self._configs.get(r.host, {})
        profile = self._normalize_profile(cfg.get("profile", r.profile))
        password = cfg.get("pjlink_password")
        if not password and profile in {"auto", "pjlink"}:
            password = cfg.get("password")
        return PJLinkClient(
            r.host, int(cfg.get("pjlink_port", r.port or 4352)),
            password=password,
            timeout=float(cfg.get("timeout", 2.0)),
        )

    @staticmethod
    def _merge_telemetry(r: ProjectorRecord, t: ProjectorTelemetry) -> None:
        for attr in (
            "manufacturer", "model", "serial_number", "software_version", "power",
            "input_source", "input_name", "av_mute", "errors", "lamp_hours", "signal",
        ):
            val = getattr(t, attr, None)
            if val is not None:
                setattr(r, attr, val)
        if t.name:
            r.name = t.name
        if t.available_inputs:
            r.available_inputs = list(t.available_inputs)
        if t.error_detail:
            r.error_detail = dict(t.error_detail)
        if t.temperatures_c:
            r.temperatures_c.update(t.temperatures_c)
            r.temperature_c = max(r.temperatures_c.values())
        if t.fans_rpm:
            r.fans_rpm.update(t.fans_rpm)
        if t.source_hours:
            r.source_hours.update(t.source_hours)
        r.telemetry_source = t.source
        r.transport = t.source
        r.authenticated = t.authenticated
        r.auth_method = t.auth_method
        r.capabilities = sorted(set(r.capabilities) | set(t.capabilities))
        if t.raw.get("pjlink_class"):
            r.pjlink_class = str(t.raw["pjlink_class"])
        for key in ("filter_hours", "lamp_replacement", "filter_replacement", "input_resolution", "recommended_resolution"):
            if t.raw.get(key) is not None:
                value = t.raw[key]
                if key == "filter_hours":
                    try: value = int(value)
                    except (ValueError, TypeError): pass
                setattr(r, key, value)
        if t.raw.get("other_info") is not None:
            r.other_info = str(t.raw["other_info"])

        if r.errors and len(r.errors) >= 6 and set(r.errors[:6]).issubset({"0", "1", "2"}):
            r.error_detail = {name: _ERROR_LEVEL.get(level, "unknown") for name, level in zip(_ERROR_NAMES, r.errors[:6])}

    def _poll_one(self, r: ProjectorRecord) -> ProjectorRecord:
        r.reachable = False
        r.valid_telemetry = False
        errors: list[str] = []
        adapter = self._adapter_for(r)
        # Explicit vendor adapter gets first chance. PJLink is then used as a
        # standards-based identity/fallback/enrichment channel when available.
        if adapter is not None:
            try:
                t = adapter.poll()
                self._merge_telemetry(r, t)
                r.reachable = True
                r.valid_telemetry = True
            except Exception as exc:
                errors.append(f"{type(adapter).__name__}: {exc}")

        profile = self._normalize_profile(self._configs.get(r.host, {}).get("profile", r.profile))
        if adapter is None or bool(self._configs.get(r.host, {}).get("pjlink_fallback", True)):
            # Profiles deliberately marked as unsupported binary/proprietary do
            # not receive a made-up ASCII implementation; PJLink is still safe.
            try:
                t = self._pjlink_client_for(r).poll()
                self._merge_telemetry(r, t)
                r.reachable = True
                r.valid_telemetry = True
            except ProjectorAuthError as exc:
                errors.append(str(exc))
                r.reachable = True
            except Exception as exc:
                errors.append(f"PJLink: {exc}")

        if r.valid_telemetry:
            r.online = True
            r.stale = False
            r.last_error = None if not errors else "; ".join(errors)
            r.last_seen_monotonic = time.monotonic()
            r.last_success_monotonic = r.last_seen_monotonic
            r.age_s = 0.0
            r.telemetry_age_s = 0.0
        else:
            r.online = False
            r.last_error = "; ".join(errors) if errors else f"no adapter for profile {profile}"
        return r

    @staticmethod
    def _broadcast_targets() -> list[tuple[str, str]]:
        """Return (local IPv4, directed broadcast) pairs for UP interfaces."""
        out: list[tuple[str, str]] = []
        try:
            import psutil
            stats = psutil.net_if_stats()
            for name, rows in psutil.net_if_addrs().items():
                if stats.get(name) and not stats[name].isup:
                    continue
                for row in rows:
                    if row.family != socket.AF_INET or not row.address or row.address.startswith("127."):
                        continue
                    if not row.netmask:
                        continue
                    try:
                        net = ipaddress.IPv4Network(f"{row.address}/{row.netmask}", strict=False)
                        out.append((row.address, str(net.broadcast_address)))
                    except ValueError:
                        continue
        except Exception:
            pass
        return sorted(set(out))

    @classmethod
    def _discover_sync(cls, timeout: float = 10.5) -> list[dict[str, str]]:
        found: dict[str, dict[str, str]] = {}
        targets = cls._broadcast_targets()
        # A separate per-interface deadline prevents the first interface from
        # consuming the global timeout and starving every remaining NIC.
        per_interface = max(0.25, min(float(timeout), float(timeout) / max(1, len(targets))))
        for local_ip, broadcast in targets:
            deadline = time.monotonic() + per_interface
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((local_ip, 0))
                sock.settimeout(min(0.25, per_interface))
                sock.sendto(b"%2SRCH\r", (broadcast, 4352))
                while time.monotonic() < deadline:
                    try:
                        data, addr = sock.recvfrom(512)
                    except socket.timeout:
                        continue
                    text = data.decode("ascii", "replace").strip()
                    m = re.match(r"%2ACKN=([0-9A-Fa-f:]{17})", text)
                    if m:
                        found[addr[0]] = {"host": addr[0], "mac": m.group(1).lower(), "interface": local_ip}
            finally:
                sock.close()
        return list(found.values())

    async def async_discover(self, timeout: float = 10.5) -> int:
        try:
            rows = await asyncio.get_running_loop().run_in_executor(_PROJECTOR_EXECUTOR, self._discover_sync, timeout)
            self.last_discovery_monotonic = time.monotonic()
            self.discovery_errors.clear()
            for row in rows:
                self._ensure_record(host=row["host"], name=row["host"], discovered=True, mac=row.get("mac"), source_interface=row.get("interface"))
            return len(rows)
        except Exception as exc:
            self.discovery_errors = [str(exc)]
            return 0

    async def async_update(self):
        now = time.monotonic()
        if self.last_discovery_monotonic is None or now - self.last_discovery_monotonic > 300:
            await self.async_discover(timeout=10.5)
        if self.records:
            results = await asyncio.gather(
                *(asyncio.get_running_loop().run_in_executor(_PROJECTOR_EXECUTOR, self._poll_one, r) for r in self.records),
                return_exceptions=True,
            )
            now = time.monotonic()
            for r, result in zip(self.records, results):
                if isinstance(result, Exception):
                    r.online = False
                    r.last_error = str(result)
                if r.last_seen_monotonic is not None:
                    r.age_s = round(max(0.0, now - r.last_seen_monotonic), 1)
                if r.last_success_monotonic is not None:
                    r.telemetry_age_s = round(max(0.0, now - r.last_success_monotonic), 1)
                    r.stale = r.telemetry_age_s > 30.0
                    if r.stale:
                        r.online = False

    def snapshot(self):
        # Credentials remain only in _configs and are never serialized.
        return [asdict(r) for r in self.records]

    def status(self) -> dict[str, Any]:
        rows = self.snapshot()
        return {
            "total": len(rows),
            "online": sum(1 for r in rows if r.get("online")),
            "reachable": sum(1 for r in rows if r.get("reachable")),
            "valid_telemetry": sum(1 for r in rows if r.get("valid_telemetry")),
            "stale": sum(1 for r in rows if r.get("stale")),
            "errors": sum(1 for r in rows if r.get("errors") and str(r.get("errors")).lower() not in {"000000", "ok", "normal", "none", "0"}),
            "discovered": sum(1 for r in rows if r.get("discovered")),
            "last_discovery_age_s": None if self.last_discovery_monotonic is None else round(time.monotonic() - self.last_discovery_monotonic, 1),
            "discovery_errors": list(self.discovery_errors),
            "projectors": rows,
        }
