"""Read-only bridge client for L-Acoustics LA_avdecc.

LA_avdecc is a C++17 library and cannot be installed as a normal Home Assistant
Python requirement. Show Network therefore consumes a tiny local/helper bridge
that wraps the official library and exposes JSON. This module does *not* fake an
AVDECC stack in Python.

Expected GET endpoint response (minimum):
{
  "entities": [{
    "entity_id": "001b92...", "manufacturer": "L-Acoustics",
    "model": "LA12X", "name": "AMP-L", "serial": "...",
    "firmware": "...", "online": true, "last_seen": 1700000000.0,
    "streams": [...], "counters": {...}, "clock": {...}, "controls": [...]
  }]
}

Only keys explicitly returned by the helper are exposed as telemetry.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import time
from typing import Any
from urllib.request import Request, urlopen


@dataclass
class AVDECCEntity:
    entity_id: str
    manufacturer: str | None = None
    model: str | None = None
    name: str | None = None
    serial: str | None = None
    firmware: str | None = None
    host: str | None = None
    online: bool = False
    last_seen: float | None = None
    streams: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, Any] = field(default_factory=dict)
    clock: dict[str, Any] = field(default_factory=dict)
    controls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "AVDECCEntity":
        entity_id = str(raw.get("entity_id") or raw.get("entityId") or "").strip()
        if not entity_id:
            raise ValueError("AVDECC entity is missing entity_id")
        manufacturer = raw.get("manufacturer")
        model = raw.get("model") or raw.get("model_name")
        return cls(
            entity_id=entity_id,
            manufacturer=str(manufacturer) if manufacturer else None,
            model=str(model) if model else None,
            name=str(raw.get("name") or raw.get("entity_name") or "") or None,
            serial=str(raw.get("serial") or raw.get("serial_number") or "") or None,
            firmware=str(raw.get("firmware") or raw.get("firmware_version") or "") or None,
            host=str(raw.get("host") or raw.get("ip") or "") or None,
            online=bool(raw.get("online", True)),
            last_seen=float(raw["last_seen"]) if raw.get("last_seen") is not None else None,
            streams=list(raw.get("streams") or []),
            counters=dict(raw.get("counters") or {}),
            clock=dict(raw.get("clock") or {}),
            controls=list(raw.get("controls") or []),
            error=str(raw.get("error")) if raw.get("error") else None,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "name": self.name,
            "serial": self.serial,
            "firmware": self.firmware,
            "host": self.host,
            "online": self.online,
            "last_seen": self.last_seen,
            "streams": list(self.streams),
            "counters": dict(self.counters),
            "clock": dict(self.clock),
            "controls": list(self.controls),
            "error": self.error,
            "protocol": "AVDECC/Milan",
            "source": "la_avdecc_bridge",
        }


class AVDECCBridgeMonitor:
    def __init__(self, endpoint: str, interval_s: float = 5.0, timeout_s: float = 2.5, token: str | None = None) -> None:
        self.endpoint = endpoint.strip()
        self.interval_s = float(interval_s)
        self.timeout_s = float(timeout_s)
        self.token = str(token).strip() if token else None
        self.records: dict[str, AVDECCEntity] = {}
        self.last_error: str | None = None
        self.last_poll: float | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if not self.endpoint:
            return
        self._task = asyncio.create_task(self._loop(), name="show-network-avdecc-bridge")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self.interval_s)

    def _fetch(self) -> dict[str, Any]:
        headers = {"Accept": "application/json", "User-Agent": "Show-Network/0.15.5"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(self.endpoint, headers=headers)
        with urlopen(req, timeout=self.timeout_s) as response:  # nosec B310 - admin-configured local endpoint
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("AVDECC bridge response too large")
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("AVDECC bridge payload must be an object")
        return payload

    async def poll_once(self) -> None:
        self.last_poll = time.time()
        try:
            payload = await asyncio.to_thread(self._fetch)
            entities = payload.get("entities") or []
            if not isinstance(entities, list):
                raise ValueError("AVDECC bridge entities must be a list")
            next_records: dict[str, AVDECCEntity] = {}
            for row in entities:
                if not isinstance(row, dict):
                    continue
                entity = AVDECCEntity.from_payload(row)
                next_records[entity.entity_id] = entity
            self.records = next_records
            self.last_error = None
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self.last_error = f"{type(err).__name__}: {err}"

    def snapshot(self) -> dict[str, Any]:
        rows = [rec.snapshot() for rec in self.records.values()]
        return {
            "avdecc_entities": sorted(rows, key=lambda row: (row.get("manufacturer") or "", row.get("name") or row["entity_id"])),
            "avdecc_total": len(rows),
            "avdecc_online": sum(1 for row in rows if row["online"]),
            "avdecc_bridge_configured": bool(self.endpoint),
            "avdecc_bridge_error": self.last_error,
            "avdecc_bridge_last_poll": self.last_poll,
            "avdecc_implementation": "L-Acoustics/avdecc helper bridge",
        }
