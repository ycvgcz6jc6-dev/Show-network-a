"""Generic OSC mapping engine.

OSC is a transversal CONTROL input. Destinations are abstract and can include
Home Assistant entities, scenes, lights, climate, media players, or a future
grandMA3 adapter. This module itself never transmits OSC or DMX.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from typing import Any

@dataclass
class Mapping:
    mapping_id: str
    address: str
    destination: str
    target: str
    attribute: str | None = None
    in_min: float = 0.0
    in_max: float = 1.0
    out_min: float = 0.0
    out_max: float = 1.0
    invert: bool = False
    deadband: float = 0.0
    min_interval_ms: int = 0
    enabled: bool = True

@dataclass
class MappingResult:
    mapping_id: str
    accepted: bool
    value: Any = None
    reason: str = ""
    timestamp: float = 0.0

class MappingEngine:
    def __init__(self):
        self.mappings: dict[str,Mapping] = {}
        self._last: dict[str,tuple[float,float]] = {}

    def add(self, mapping: Mapping):
        self.mappings[mapping.mapping_id]=mapping

    def remove(self, mapping_id):
        self.mappings.pop(mapping_id,None)
        self._last.pop(mapping_id,None)

    def _scale(self, value, mapping):
        x=float(value)
        span=mapping.in_max-mapping.in_min
        if span == 0:
            raise ValueError("input range cannot be zero")
        x=(x-mapping.in_min)/span
        x=max(0.0,min(1.0,x))
        if mapping.invert: x=1.0-x
        return mapping.out_min+x*(mapping.out_max-mapping.out_min)

    def process(self, address, value, now=None):
        now=monotonic() if now is None else now
        results=[]
        for m in self.mappings.values():
            if not m.enabled or m.address != address:
                continue
            try:
                out=self._scale(value,m)
            except (TypeError,ValueError) as exc:
                results.append(MappingResult(m.mapping_id,False,reason=str(exc),timestamp=now))
                continue

            previous=self._last.get(m.mapping_id)
            if previous:
                last_time,last_value=previous
                if m.min_interval_ms and (now-last_time)*1000 < m.min_interval_ms:
                    results.append(MappingResult(m.mapping_id,False,reason="rate_limited",timestamp=now))
                    continue
                if m.deadband and abs(out-last_value) < m.deadband:
                    results.append(MappingResult(m.mapping_id,False,reason="deadband",timestamp=now))
                    continue

            self._last[m.mapping_id]=(now,out)
            results.append(MappingResult(m.mapping_id,True,out,"accepted",now))
        return results
