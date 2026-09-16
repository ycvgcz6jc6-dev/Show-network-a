"""Passive RDM / RDMnet device inventory.

This module never speaks RDM itself. It only normalizes whatever device
rows an external bridge exposes -- typically an OLA (Open Lighting
Architecture) RDM client or an RDMnet gateway -- into one consistent
snapshot shape. RDM *writes* (identify, DMX address changes, personality
changes) are handled, if at all, by the bridge itself and are outside this
module's scope entirely: this is read-only identity/telemetry aggregation.

Note for whoever wires this up in runtime/setup.py: as of this audit,
neither ``rdm_bridge`` nor ``rdmnet_bridge`` exist anywhere in this
codebase, so this inventory will legitimately stay empty until one is
built. Accepting both dict-like and attribute-style rows here is a
deliberate hedge against not knowing that future bridge's exact row shape.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

_STALE_AFTER_S = 60.0


def _field(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


@dataclass
class RDMDevice:
    uid: str
    transport: str
    manufacturer: str | None = None
    model: str | None = None
    label: str | None = None
    dmx_address: int | None = None
    footprint: int | None = None
    personality: int | None = None
    personality_count: int | None = None
    sensors: list[Any] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class RDMInventory:
    def __init__(self, stale_after_s: float = _STALE_AFTER_S) -> None:
        self.devices: dict[str, RDMDevice] = {}
        self.stale_after_s = float(stale_after_s)

    def ingest(self, rows: list[Any] | None, transport: str) -> None:
        """Merge a batch of device rows from one bridge (OLA/RDMnet).

        Rows may be plain dicts or objects; whichever fields are present are
        used, missing ones are left as-is on an existing record (a
        newer partial observation never blanks out a previously known
        manufacturer/model, for example).
        """
        now = time.time()
        for row in rows or ():
            raw_uid = _field(row, "uid")
            if raw_uid is None:
                raw_uid = _field(row, "UID")
            if not raw_uid:
                continue
            uid = str(raw_uid)
            device = self.devices.get(uid)
            if device is None:
                device = RDMDevice(uid=uid, transport=transport, first_seen=now, last_seen=now)
                self.devices[uid] = device
            device.transport = transport
            device.last_seen = now
            device.manufacturer = _field(row, "manufacturer") or device.manufacturer
            device.model = _field(row, "model") or device.model
            device.label = _field(row, "label") or _field(row, "device_label") or device.label

            address = _field(row, "dmx_address")
            if address is None:
                address = _field(row, "start_address")
            if address is not None:
                try:
                    device.dmx_address = int(address)
                except (TypeError, ValueError):
                    pass

            footprint = _field(row, "footprint")
            if footprint is not None:
                try:
                    device.footprint = int(footprint)
                except (TypeError, ValueError):
                    pass

            personality = _field(row, "personality")
            if personality is not None:
                try:
                    device.personality = int(personality)
                except (TypeError, ValueError):
                    pass

            personality_count = _field(row, "personality_count")
            if personality_count is not None:
                try:
                    device.personality_count = int(personality_count)
                except (TypeError, ValueError):
                    pass

            sensors = _field(row, "sensors")
            if sensors:
                try:
                    device.sensors = list(sensors)
                except TypeError:
                    pass

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        rows = []
        for device in sorted(self.devices.values(), key=lambda d: d.uid):
            age = max(0.0, now - device.last_seen)
            rows.append({
                "uid": device.uid,
                "transport": device.transport,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "label": device.label,
                "dmx_address": device.dmx_address,
                "footprint": device.footprint,
                "personality": device.personality,
                "personality_count": device.personality_count,
                "sensors": device.sensors,
                "first_seen": device.first_seen,
                "last_seen": device.last_seen,
                "age_s": round(age, 1),
                "fresh": age < self.stale_after_s,
            })
        return {
            "rdm_devices": rows,
            "rdm_device_count": len(rows),
            "rdm_fresh_count": sum(1 for r in rows if r["fresh"]),
            "rdm_transports": sorted({d.transport for d in self.devices.values()}),
            "rdm_note": "Populated only when an OLA (RDM) or RDMnet gateway bridge is configured and running; this module never speaks RDM itself.",
        }
