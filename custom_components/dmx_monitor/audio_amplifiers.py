"""Read-only audio amplifier health model.

This module deliberately separates manufacturer capability from live telemetry.
It never invents temperature/status values: a value is only exposed when an
actual observer supplies it. Passive Dante/mDNS observations can create a
candidate device, while vendor-specific telemetry adapters can enrich it.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import time

STALE_S = 20.0

@dataclass
class AmplifierRecord:
    key: str
    manufacturer: str
    model: str | None = None
    host: str | None = None
    protocol: str | None = None
    online: bool = False
    status: str = "unknown"
    error: str | None = None
    temperature_c: float | None = None
    temperatures: dict[str, float] = field(default_factory=dict)
    input_level: dict[str, float] = field(default_factory=dict)
    output_level: dict[str, float] = field(default_factory=dict)
    load: dict[str, float] = field(default_factory=dict)
    limiter: dict[str, bool] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    evidence: list[str] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {
            "key": self.key, "manufacturer": self.manufacturer, "model": self.model,
            "host": self.host, "protocol": self.protocol, "online": self.online,
            "status": self.status, "error": self.error,
            "temperature_c": self.temperature_c,
            "temperatures": dict(self.temperatures),
            "input_level": dict(self.input_level), "output_level": dict(self.output_level),
            "load": dict(self.load), "limiter": dict(self.limiter),
            "first_seen": self.first_seen, "last_seen": self.last_seen,
            "evidence": list(self.evidence),
        }

class AudioAmplifierInventory:
    """Small vendor-neutral registry for amplifier telemetry."""
    def __init__(self, stale_s: float = STALE_S) -> None:
        self.stale_s = float(stale_s)
        self.records: dict[str, AmplifierRecord] = {}

    def observe(self, *, key: str, manufacturer: str, host: str | None = None,
                model: str | None = None, protocol: str | None = None,
                evidence: str | None = None) -> AmplifierRecord:
        now = time.time()
        rec = self.records.get(key)
        if rec is None:
            rec = AmplifierRecord(key=key, manufacturer=manufacturer, host=host,
                                  model=model, protocol=protocol, first_seen=now, last_seen=now)
            self.records[key] = rec
        rec.last_seen = now
        rec.online = True
        if host: rec.host = host
        if model: rec.model = model
        if protocol: rec.protocol = protocol
        if evidence and evidence not in rec.evidence: rec.evidence.append(evidence)
        return rec

    def update_telemetry(self, key: str, **values) -> None:
        rec = self.records.get(key)
        if not rec:
            return
        rec.last_seen = time.time()
        for name in ("status", "error", "temperature_c", "temperatures", "input_level",
                     "output_level", "load", "limiter"):
            if name in values and values[name] is not None:
                setattr(rec, name, values[name])

    def snapshot(self) -> dict:
        now = time.time()
        rows=[]
        for rec in self.records.values():
            rec.online = (now - rec.last_seen) <= self.stale_s
            rows.append(rec.snapshot())
        temps=[r.temperature_c for r in self.records.values() if r.temperature_c is not None]
        errors=sum(1 for r in self.records.values() if r.error)
        return {
            "audio_amplifiers": sorted(rows, key=lambda r: (r["manufacturer"], r["host"] or r["key"])),
            "audio_amplifiers_total": len(rows),
            "audio_amplifiers_online": sum(1 for r in self.records.values() if r.online),
            "audio_amplifiers_errors": errors,
            "audio_amplifier_temperature_max": max(temps) if temps else None,
            "audio_amplifier_stale_timeout_s": self.stale_s,
        }
