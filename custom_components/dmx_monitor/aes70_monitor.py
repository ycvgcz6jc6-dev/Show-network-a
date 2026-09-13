"""Real AES70/OCA controller integration for vendor audio devices.

This module speaks AES70 over TCP through the open-source AES70py controller.
It is vendor-neutral at the wire level; d&b audiotechnik devices are the first
manufacturer profile explicitly mapped to it because d&b R1 uses OCA/AES70.
No values are fabricated: device-manager fields and the discovered OCA role map
are queried from the remote device.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from .security import ip_allowed, normalize_ip_allowlist
from .flow_pipeline import AsyncGate

_LOGGER = logging.getLogger(__name__)
DEFAULT_PORT = 65000


def _plain(value: Any) -> Any:
    """Convert common AES70 wrapper objects into JSON-friendly values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if hasattr(value, "__dict__"):
        data = {}
        for key, item in vars(value).items():
            if key.startswith("_"):
                continue
            try:
                data[key] = _plain(item)
            except Exception:
                pass
        return data or str(value)
    return str(value)


@dataclass
class AES70Record:
    host: str
    port: int
    manufacturer: str | None = None
    model: str | None = None
    device_name: str | None = None
    serial: str | None = None
    device_role: str | None = None
    oca_version: Any = None
    state: Any = None
    message: str | None = None
    roles: list[str] = field(default_factory=list)
    online: bool = False
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "device_name": self.device_name,
            "serial": self.serial,
            "device_role": self.device_role,
            "oca_version": _plain(self.oca_version),
            "state": _plain(self.state),
            "message": self.message,
            "roles": list(self.roles),
            "online": self.online,
            "error": self.error,
            "protocol": "AES70/OCA",
            "source": "live_aes70",
        }


class AES70Monitor:
    """Poll configured AES70 devices using the real OCP.1 protocol."""

    def __init__(self, hosts: list[str], port: int = DEFAULT_PORT, interval_s: float = 10.0, allowed_sources=None, concurrency: int = 4) -> None:
        self.hosts = list(dict.fromkeys(h.strip() for h in hosts if h.strip()))
        self.allowed_sources = normalize_ip_allowlist(allowed_sources)
        self._gate = AsyncGate(concurrency)
        self.port = int(port)
        self.interval_s = float(interval_s)
        self.records: dict[str, AES70Record] = {}
        self._task: asyncio.Task | None = None
        self._clients: dict[str, Any] = {}

    async def start(self) -> None:
        if not self.hosts:
            return
        # Validate dependency at runtime so pure Show Network tests remain HA-independent.
        try:
            import aes70.controller.tcp_connection as tcp_connection  # type: ignore
            from aes70.controller.remote_device import RemoteDevice  # type: ignore
        except ImportError as err:
            raise RuntimeError("AES70py >= 1.0.3 is required for AES70 monitoring") from err
        self._tcp_connection = tcp_connection
        self._RemoteDevice = RemoteDevice
        self._task = asyncio.create_task(self._loop(), name="show-network-aes70")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        for client in list(self._clients.values()):
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()

    async def _loop(self) -> None:
        while True:
            tasks = [asyncio.create_task(self._poll_guarded(host), name=f"show-network-aes70-poll-{host}") for host in self.hosts]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(self.interval_s)

    async def _poll_guarded(self, host: str) -> None:
        if not ip_allowed(host, self.allowed_sources):
            rec = self.records.setdefault(host, AES70Record(host, self.port))
            rec.online = False
            rec.error = "source rejected by IP allowlist"
            return
        try:
            await self._gate.run(lambda: self._poll(host))
        except asyncio.CancelledError:
            raise
        except Exception as err:
            rec = self.records.setdefault(host, AES70Record(host, self.port))
            rec.online = False
            rec.error = f"{type(err).__name__}: {err}"
            _LOGGER.debug("AES70 %s unavailable: %s", host, err)

    async def _poll(self, host: str) -> None:
        # AES70py is async, but its TCP connection setup is synchronous.
        client = await asyncio.to_thread(self._tcp_connection.connect, host=host, port=self.port)
        device = self._RemoteDevice(client)
        self._clients[host] = device
        rec = AES70Record(host, self.port)
        try:
            dm = device.DeviceManager
            calls = {
                "oca_version": dm.GetOcaVersion,
                "serial": dm.GetSerialNumber,
                "device_name": dm.GetDeviceName,
                "device_role": dm.GetDeviceRole,
                "state": dm.GetState,
                "message": dm.GetMessage,
                "model": dm.GetModelDescription,
            }
            results = await asyncio.gather(*(fn() for fn in calls.values()), return_exceptions=True)
            for (key, _), value in zip(calls.items(), results):
                if not isinstance(value, Exception):
                    setattr(rec, key, _plain(value))
            # AES70 model descriptions commonly carry manufacturer/model/version text.
            model_desc = rec.model
            if isinstance(model_desc, dict):
                text = " ".join(str(v) for v in model_desc.values() if v is not None)
                rec.model = text or None
            if rec.model and "d&b" in rec.model.lower():
                rec.manufacturer = "d&b audiotechnik"
            elif rec.device_name and "d&b" in rec.device_name.lower():
                rec.manufacturer = "d&b audiotechnik"
            roles = await device.get_role_map()
            rec.roles = sorted(str(k) for k in roles.keys())
            rec.online = True
            rec.error = None
        finally:
            rec_snapshot = rec
            self.records[host] = rec_snapshot
            try:
                device.close()
            except Exception:
                pass
            self._clients.pop(host, None)

    def snapshot(self) -> dict[str, Any]:
        rows = [record.snapshot() for record in self.records.values()]
        return {
            "aes70_devices": sorted(rows, key=lambda row: row["host"]),
            "aes70_total": len(rows),
            "aes70_online": sum(1 for row in rows if row["online"]),
            "aes70_protocol": "AES70/OCA (OCP.1)",
        }
