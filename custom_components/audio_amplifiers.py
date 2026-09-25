"""Vendor-neutral amplifier inventory fed only by real observations.

Discovery and telemetry freshness are intentionally separated. A stale mDNS or
Dante snapshot must not be able to keep an amplifier falsely ONLINE merely
because Home Assistant refreshed the coordinator.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Any

STALE_S = 30.0


def _merge_dict(dst: dict, src: dict | None) -> dict:
    if not src:
        return dst
    for key, value in src.items():
        if value is not None:
            dst[str(key)] = value
    return dst


@dataclass
class AmplifierRecord:
    key: str
    manufacturer: str
    model: str | None = None
    serial: str | None = None
    host: str | None = None
    entity_id: str | None = None
    device_name: str | None = None
    firmware: str | None = None
    protocols: set[str] = field(default_factory=set)
    telemetry_sources: set[str] = field(default_factory=set)
    online: bool = False
    status: str = "unknown"
    error: str | None = None
    temperature_c: float | None = None
    temperatures: dict[str, float] = field(default_factory=dict)
    input_level: dict[str, float] = field(default_factory=dict)
    output_level: dict[str, float] = field(default_factory=dict)
    load: dict[str, float] = field(default_factory=dict)
    limiter: dict[str, bool] = field(default_factory=dict)
    mute: dict[str, bool] = field(default_factory=dict)
    streams: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, Any] = field(default_factory=dict)
    clock: dict[str, Any] = field(default_factory=dict)
    controls: list[dict[str, Any]] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    last_telemetry: float | None = None
    evidence: list[str] = field(default_factory=list)

    def snapshot(self, now: float, stale_s: float) -> dict:
        age = max(0.0, now - self.last_seen)
        telemetry_age = None if self.last_telemetry is None else max(0.0, now - self.last_telemetry)
        self.online = age <= stale_s
        return {
            "key": self.key,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial": self.serial,
            "host": self.host,
            "entity_id": self.entity_id,
            "device_name": self.device_name,
            "firmware": self.firmware,
            "protocols": sorted(self.protocols),
            "telemetry_sources": sorted(self.telemetry_sources),
            "online": self.online,
            "status": self.status,
            "error": self.error,
            "temperature_c": self.temperature_c,
            "temperatures": dict(self.temperatures),
            "input_level": dict(self.input_level),
            "output_level": dict(self.output_level),
            "load": dict(self.load),
            "limiter": dict(self.limiter),
            "mute": dict(self.mute),
            "streams": list(self.streams),
            "counters": dict(self.counters),
            "clock": dict(self.clock),
            "controls": list(self.controls),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_telemetry": self.last_telemetry,
            "age_s": round(age, 3),
            "telemetry_age_s": None if telemetry_age is None else round(telemetry_age, 3),
            "evidence": list(self.evidence),
        }


class AudioAmplifierInventory:
    """Registry for amplifier identity and genuinely sourced telemetry."""

    def __init__(self, stale_s: float = STALE_S) -> None:
        self.stale_s = float(stale_s)
        self.records: dict[str, AmplifierRecord] = {}

    def remove(self, key: str) -> None:
        self.records.pop(key, None)

    def observe(
        self,
        *,
        key: str,
        manufacturer: str,
        host: str | None = None,
        model: str | None = None,
        protocol: str | None = None,
        evidence: str | None = None,
        observed_at: float | None = None,
        serial: str | None = None,
        entity_id: str | None = None,
        device_name: str | None = None,
        firmware: str | None = None,
    ) -> AmplifierRecord:
        now = float(observed_at if observed_at is not None else time.time())
        rec = self.records.get(key)
        if rec is None:
            rec = AmplifierRecord(
                key=key,
                manufacturer=manufacturer,
                host=host,
                model=model,
                serial=serial,
                entity_id=entity_id,
                device_name=device_name,
                firmware=firmware,
                first_seen=now,
                last_seen=now,
            )
            self.records[key] = rec
        # Never move time backwards and never make an old replay fresh.
        if now >= rec.last_seen:
            rec.last_seen = now
        rec.manufacturer = manufacturer or rec.manufacturer
        if host:
            rec.host = host
        if model:
            rec.model = model
        if serial:
            rec.serial = serial
        if entity_id:
            rec.entity_id = entity_id
        if device_name:
            rec.device_name = device_name
        if firmware:
            rec.firmware = firmware
        if protocol:
            rec.protocols.add(protocol)
        if evidence and evidence not in rec.evidence:
            rec.evidence.append(evidence)
        return rec

    def update_telemetry(self, key: str, *, observed_at: float | None = None, source: str | None = None, **values) -> None:
        rec = self.records.get(key)
        if not rec:
            return
        now = float(observed_at if observed_at is not None else time.time())
        if rec.last_telemetry is not None and now < rec.last_telemetry:
            return
        rec.last_telemetry = now
        if now >= rec.last_seen:
            rec.last_seen = now
        if source:
            rec.telemetry_sources.add(source)
            rec.protocols.add(source)
        for name in ("status", "error", "temperature_c", "streams", "controls"):
            if name in values and values[name] is not None:
                setattr(rec, name, values[name])
        for name in ("temperatures", "input_level", "output_level", "load", "limiter", "mute", "counters", "clock"):
            if name in values and values[name] is not None:
                _merge_dict(getattr(rec, name), values[name])

    def snapshot(self) -> dict:
        now = time.time()
        rows = [rec.snapshot(now, self.stale_s) for rec in self.records.values()]
        temps = [r["temperature_c"] for r in rows if r["temperature_c"] is not None]
        errors = sum(1 for r in rows if r["error"])
        return {
            "audio_amplifiers": sorted(rows, key=lambda r: (r["manufacturer"], r["host"] or r["key"])),
            "audio_amplifiers_total": len(rows),
            "audio_amplifiers_online": sum(1 for r in rows if r["online"]),
            "audio_amplifiers_errors": errors,
            "audio_amplifier_temperature_max": max(temps) if temps else None,
            "audio_amplifier_stale_timeout_s": self.stale_s,
        }
