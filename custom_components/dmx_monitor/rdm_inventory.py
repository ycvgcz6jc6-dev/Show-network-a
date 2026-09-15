"""RDM / RDMnet device inventory.

The inventory only exposes values that came from an RDM/RDMnet transport.
Discovery identity and telemetry freshness are kept separate so a cached UID does
not keep a responder artificially online.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from typing import Any

_UID_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{8}$")


def normalize_uid(value: str) -> str:
    value = str(value or "").strip().lower().replace("-", ":")
    if not _UID_RE.match(value):
        raise ValueError(f"Invalid RDM UID: {value!r}")
    return value


@dataclass
class RDMDevice:
    uid: str
    transport: str
    universe: int | None = None
    scope: str | None = None
    manufacturer_label: str | None = None
    model_description: str | None = None
    device_label: str | None = None
    software_version_label: str | None = None
    dmx_start_address: int | None = None
    dmx_footprint: int | None = None
    current_personality: int | None = None
    personality_count: int | None = None
    sub_device_count: int | None = None
    sensor_count: int | None = None
    supported_parameters: list[str] = field(default_factory=list)
    sensors: list[dict[str, Any]] = field(default_factory=list)
    status_messages: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    last_telemetry: float | None = None
    source: str | None = None

    def update(self, row: dict[str, Any], observed_at: float) -> None:
        self.last_seen = max(self.last_seen, observed_at)
        for key in (
            "manufacturer_label", "model_description", "device_label",
            "software_version_label", "dmx_start_address", "dmx_footprint",
            "current_personality", "personality_count", "sub_device_count",
            "sensor_count", "scope", "universe", "source",
        ):
            if row.get(key) is not None:
                setattr(self, key, row[key])
        for key in ("supported_parameters", "sensors", "status_messages"):
            if isinstance(row.get(key), list):
                setattr(self, key, list(row[key]))
        if isinstance(row.get("extra"), dict):
            self.extra.update({str(k): v for k, v in row["extra"].items() if v is not None})
        if any(row.get(k) is not None for k in (
            "manufacturer_label", "model_description", "device_label",
            "software_version_label", "dmx_start_address", "dmx_footprint",
            "current_personality", "supported_parameters", "sensors", "status_messages",
        )):
            self.last_telemetry = max(self.last_telemetry or 0.0, observed_at)

    def snapshot(self, now: float, stale_s: float) -> dict[str, Any]:
        age = max(0.0, now - self.last_seen)
        tele_age = None if self.last_telemetry is None else max(0.0, now - self.last_telemetry)
        return {
            "uid": self.uid,
            "transport": self.transport,
            "universe": self.universe,
            "scope": self.scope,
            "manufacturer_label": self.manufacturer_label,
            "model_description": self.model_description,
            "device_label": self.device_label,
            "software_version_label": self.software_version_label,
            "dmx_start_address": self.dmx_start_address,
            "dmx_footprint": self.dmx_footprint,
            "current_personality": self.current_personality,
            "personality_count": self.personality_count,
            "sub_device_count": self.sub_device_count,
            "sensor_count": self.sensor_count,
            "supported_parameters": list(self.supported_parameters),
            "sensors": list(self.sensors),
            "status_messages": list(self.status_messages),
            "extra": dict(self.extra),
            "source": self.source,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_telemetry": self.last_telemetry,
            "age_s": round(age, 3),
            "telemetry_age_s": None if tele_age is None else round(tele_age, 3),
            "online": age <= stale_s,
            "stale": age > stale_s,
        }


class RDMInventory:
    def __init__(self, stale_s: float = 45.0) -> None:
        self.stale_s = float(stale_s)
        self._devices: dict[tuple[str, str], RDMDevice] = {}

    def ingest(self, rows: list[dict[str, Any]], *, transport: str, observed_at: float | None = None) -> None:
        now = float(observed_at if observed_at is not None else time.time())
        for row in rows or []:
            try:
                uid = normalize_uid(row.get("uid", ""))
            except ValueError:
                continue
            key = (transport, uid)
            rec = self._devices.get(key)
            if rec is None:
                rec = RDMDevice(uid=uid, transport=transport, universe=row.get("universe"), scope=row.get("scope"), source=row.get("source"), first_seen=now, last_seen=now)
                self._devices[key] = rec
            rec.update(row, float(row.get("last_seen") or now))

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        rows = [d.snapshot(now, self.stale_s) for d in self._devices.values()]
        rows.sort(key=lambda d: (d["transport"], d.get("universe") or 0, d["uid"]))
        return {
            "rdm_devices": rows,
            "rdm_devices_total": len(rows),
            "rdm_devices_online": sum(1 for r in rows if r["online"]),
            "rdm_stale_timeout_s": self.stale_s,
            "rdm_transports": sorted({r["transport"] for r in rows}),
        }
