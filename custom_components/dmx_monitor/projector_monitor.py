from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from dataclasses import dataclass, asdict, field
from typing import Any


_ERROR_NAMES = ("fan", "lamp", "temperature", "cover", "filter", "other")
_ERROR_LEVEL = {"0": "ok", "1": "warning", "2": "error"}


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
    error_detail: dict[str, str] = field(default_factory=dict)
    lamp_hours: int | None = None
    lamp_status: str | None = None
    filter_hours: int | None = None
    lamp_replacement: str | None = None
    filter_replacement: str | None = None
    input_resolution: str | None = None
    recommended_resolution: str | None = None
    profile: str = "auto"
    online: bool = False
    discovered: bool = False
    mac: str | None = None
    last_error: str | None = None
    last_seen_monotonic: float | None = None
    age_s: float | None = None


class PJLinkMonitor:
    """Read-only PJLink monitor with optional Class 2 broadcast discovery.

    Only PJLink GET/search operations are issued here. Active projector control
    remains isolated in projector.py behind the existing security gate.
    """

    def __init__(self, projectors: list[dict[str, Any]] | None = None):
        self.records: list[ProjectorRecord] = []
        self._by_host: dict[str, ProjectorRecord] = {}
        self.last_discovery_monotonic: float | None = None
        self.discovery_errors: list[str] = []
        for p in projectors or []:
            if p.get("host"):
                self._ensure_record(
                    host=str(p["host"]),
                    port=int(p.get("port", 4352)),
                    name=str(p.get("name") or p.get("host")),
                    profile=str(p.get("profile", "auto")),
                    discovered=False,
                    mac=p.get("mac"),
                )

    def _ensure_record(self, *, host: str, port: int = 4352, name: str | None = None,
                       profile: str = "auto", discovered: bool = False,
                       mac: str | None = None) -> ProjectorRecord:
        rec = self._by_host.get(host)
        if rec is None:
            rec = ProjectorRecord(name=name or host, host=host, port=port, profile=profile,
                                  discovered=discovered, mac=mac)
            self._by_host[host] = rec
            self.records.append(rec)
        else:
            rec.port = port or rec.port
            rec.discovered = rec.discovered or discovered
            rec.mac = mac or rec.mac
            if name and rec.name == rec.host:
                rec.name = name
        return rec

    @staticmethod
    def _payload(value: str | None) -> str | None:
        if not value or "=" not in value:
            return None
        payload = value.split("=", 1)[1].strip()
        if payload in {"ERR1", "ERR2", "ERR3", "ERR4"}:
            return None
        return payload

    @staticmethod
    def _query(host: str, port: int, cmd: str, timeout: float = 2.0) -> str:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            banner = s.recv(256)
            if not banner.startswith(b"PJLINK "):
                raise ConnectionError("not a PJLink endpoint")
            # PJLink authentication is deliberately not guessed here. If the
            # endpoint requires authentication, monitoring reports that fact.
            if banner.startswith(b"PJLINK 1") or banner.startswith(b"PJLINK 2"):
                raise PermissionError("PJLink authentication required")
            s.sendall((cmd + "\r").encode("ascii"))
            return s.recv(2048).decode("utf-8", "replace").strip()

    @classmethod
    def _poll_one(cls, r: ProjectorRecord) -> ProjectorRecord:
        class1 = {
            "power": "%1POWR ?", "input_source": "%1INPT ?", "av_mute": "%1AVMT ?",
            "errors": "%1ERST ?", "lamp": "%1LAMP ?", "available_inputs": "%1INST ?",
            "name": "%1NAME ?", "manufacturer": "%1INF1 ?", "model": "%1INF2 ?",
            "other_info": "%1INFO ?", "pjlink_class": "%1CLSS ?",
        }
        vals: dict[str, str] = {}
        for key, cmd in class1.items():
            try:
                vals[key] = cls._query(r.host, r.port, cmd)
            except PermissionError:
                raise
            except Exception:
                pass
        if not vals:
            raise ConnectionError("no PJLink response")

        p = cls._payload(vals.get("power"))
        r.power = {"0": "off", "1": "on", "2": "cooling", "3": "warming"}.get(p, p)
        r.input_source = cls._payload(vals.get("input_source"))
        a = cls._payload(vals.get("av_mute"))
        r.av_mute = {"30": "off", "31": "on", "10": "video", "20": "audio"}.get(a, a)
        r.errors = cls._payload(vals.get("errors"))
        r.error_detail = {}
        if r.errors and len(r.errors) >= 6:
            r.error_detail = {name: _ERROR_LEVEL.get(level, "unknown") for name, level in zip(_ERROR_NAMES, r.errors[:6])}

        lamp = cls._payload(vals.get("lamp"))
        if lamp:
            parts = lamp.split()
            try:
                r.lamp_hours = int(parts[0])
            except (TypeError, ValueError):
                pass
            if len(parts) > 1:
                r.lamp_status = "on" if parts[1] == "1" else "off" if parts[1] == "0" else parts[1]

        inputs = cls._payload(vals.get("available_inputs"))
        r.available_inputs = inputs.split() if inputs else []
        r.name = cls._payload(vals.get("name")) or r.name
        r.manufacturer = cls._payload(vals.get("manufacturer")) or r.manufacturer
        r.model = cls._payload(vals.get("model")) or r.model
        r.other_info = cls._payload(vals.get("other_info")) or r.other_info
        r.pjlink_class = cls._payload(vals.get("pjlink_class")) or r.pjlink_class

        if r.pjlink_class and r.pjlink_class.startswith("2"):
            class2 = {
                "serial_number": "%2SNUM ?", "software_version": "%2SVER ?",
                "input_resolution": "%2IRES ?", "recommended_resolution": "%2RRES ?",
                "filter_hours": "%2FILT ?", "lamp_replacement": "%2RLMP ?",
                "filter_replacement": "%2RFIL ?",
            }
            for key, cmd in class2.items():
                try:
                    value = cls._payload(cls._query(r.host, r.port, cmd))
                except Exception:
                    value = None
                if value is None:
                    continue
                if key == "filter_hours":
                    try:
                        r.filter_hours = int(value)
                    except ValueError:
                        pass
                else:
                    setattr(r, key, value)
            if r.input_source:
                try:
                    r.input_name = cls._payload(cls._query(r.host, r.port, f"%2INNM ?{r.input_source}"))
                except Exception:
                    pass

        r.online = True
        r.last_error = None
        r.last_seen_monotonic = time.monotonic()
        r.age_s = 0.0
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
        deadline = time.monotonic() + max(0.25, timeout)
        targets = cls._broadcast_targets()
        for local_ip, broadcast in targets:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((local_ip, 0))
                sock.settimeout(0.25)
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
            rows = await asyncio.get_running_loop().run_in_executor(None, self._discover_sync, timeout)
            self.last_discovery_monotonic = time.monotonic()
            self.discovery_errors.clear()
            for row in rows:
                self._ensure_record(host=row["host"], name=row["host"], discovered=True, mac=row.get("mac"))
            return len(rows)
        except Exception as exc:
            self.discovery_errors = [str(exc)]
            return 0

    async def async_update(self):
        now = time.monotonic()
        # Run standards-based Class 2 discovery at startup and then at a slow
        # cadence. This is a bounded read-only broadcast search, not a port scan.
        if self.last_discovery_monotonic is None or now - self.last_discovery_monotonic > 300:
            await self.async_discover(timeout=10.5)
        if self.records:
            results = await asyncio.gather(
                *(asyncio.get_running_loop().run_in_executor(None, self._poll_one, r) for r in self.records),
                return_exceptions=True,
            )
            for r, result in zip(self.records, results):
                if isinstance(result, Exception):
                    r.online = False
                    r.last_error = str(result)
                if r.last_seen_monotonic is not None:
                    r.age_s = round(max(0.0, time.monotonic() - r.last_seen_monotonic), 1)

    def snapshot(self):
        return [asdict(r) for r in self.records]

    def status(self) -> dict[str, Any]:
        rows = self.snapshot()
        return {
            "total": len(rows),
            "online": sum(1 for r in rows if r.get("online")),
            "errors": sum(1 for r in rows if r.get("errors") and set(str(r.get("errors"))) - {"0"}),
            "discovered": sum(1 for r in rows if r.get("discovered")),
            "last_discovery_age_s": None if self.last_discovery_monotonic is None else round(time.monotonic() - self.last_discovery_monotonic, 1),
            "discovery_errors": list(self.discovery_errors),
            "projectors": rows,
        }
