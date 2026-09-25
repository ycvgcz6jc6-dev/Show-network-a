"""Generic DMX -> Home Assistant light/service mapping.

Receive-only on the show network: DMX values are consumed and translated into
Home Assistant service calls. No DMX/sACN/Art-Net output is generated.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import monotonic
from typing import Any
import math

@dataclass
class DmxHAMapping:
    mapping_id: str
    universe: int
    channels: tuple[int, ...]
    entity_id: str | None = None
    domain: str = "light"
    service: str = "turn_on"
    mode: str = "dimmer"  # dimmer, rgb, rgbw, cct, switch, service
    source: str | None = None
    min_interval_ms: int = 100
    deadband: float = 0.0
    invert: bool = False
    dimmer_curve: str = "linear"
    enabled: bool = True
    data: dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if not self.channels or any(c < 1 or c > 512 for c in self.channels):
            raise ValueError("DMX channels must be 1..512")
        if self.mode in {"rgb", "rgbw"} and len(self.channels) < (4 if self.mode == "rgbw" else 3):
            raise ValueError(f"{self.mode} mapping needs {4 if self.mode == 'rgbw' else 3} channels")
        if self.mode == "cct" and len(self.channels) < 1:
            raise ValueError("cct mapping needs at least one channel")

    def snapshot(self):
        d = asdict(self)
        d["channels"] = list(self.channels)
        return d

class DmxHAMappingEngine:
    def __init__(self):
        self.mappings: dict[str, DmxHAMapping] = {}
        self._last_sent: dict[str, tuple[float, tuple[Any, ...]]] = {}

    def add(self, mapping: DmxHAMapping):
        self.mappings[mapping.mapping_id] = mapping

    def remove(self, mapping_id: str):
        self.mappings.pop(mapping_id, None)
        self._last_sent.pop(mapping_id, None)

    @staticmethod
    def _pct(v: int, invert: bool, curve: str = "linear") -> int:
        x = max(0, min(255, int(v))) / 255.0
        if invert:
            x = 1.0 - x
        curve = (curve or "linear").lower()
        if curve == "gamma_1_8":
            y = x ** 1.8
        elif curve == "gamma_2_0":
            y = x ** 2.0
        elif curve == "gamma_2_2":
            y = x ** 2.2
        elif curve == "gamma_2_4":
            y = x ** 2.4
        elif curve in {"logarithmic", "dali_log"}:
            # DALI-like logarithmic approximation; not a DALI wire/protocol conversion.
            y = (math.exp(4.0 * x) - 1.0) / (math.exp(4.0) - 1.0)
        elif curve == "s_curve":
            y = x * x * (3.0 - 2.0 * x)
        else:
            y = x
        return round(max(0.0, min(1.0, y)) * 100)

    @staticmethod
    def _rgb(vs, invert):
        vals = [max(0, min(255, int(v))) for v in vs]
        if invert: vals = [255-v for v in vals]
        return vals

    def process(self, universe: int, source: str | None, values: bytes | list[int], now=None):
        now = monotonic() if now is None else now
        proposals = []
        for m in self.mappings.values():
            if not m.enabled or m.universe != universe:
                continue
            if m.source and m.source not in {source}:
                continue
            vals = [int(v) for v in values]
            selected = [vals[c-1] if c <= len(vals) else 0 for c in m.channels]
            service = m.service
            try:
                if m.mode == "dimmer":
                    payload = {**m.data, "brightness_pct": self._pct(selected[0], m.invert, m.dimmer_curve)}
                    keyvals = (payload.get("brightness_pct"),)
                elif m.mode == "switch":
                    on = (selected[0] if not m.invert else 255-selected[0]) > 0
                    service = "turn_on" if on else "turn_off"
                    payload = dict(m.data)
                    keyvals = (service,)
                elif m.mode == "rgb":
                    r,g,b = self._rgb(selected[:3], m.invert)
                    payload = {**m.data, "rgb_color": [r,g,b]}
                    service = m.service
                    keyvals = (r,g,b)
                elif m.mode == "rgbw":
                    r,g,b,w = self._rgb(selected[:4], m.invert)
                    payload = {**m.data, "rgbw_color": [r,g,b,w]}
                    service = m.service
                    keyvals = (r,g,b,w)
                elif m.mode == "cct":
                    payload = {**m.data, "color_temp_kelvin": round(1500 + self._pct(selected[0], m.invert) * 45)}
                    service = m.service
                    keyvals = (payload["color_temp_kelvin"],)
                else:
                    payload = dict(m.data)
                    service = m.service
                    keyvals = tuple(selected)
            except (TypeError, ValueError, IndexError):
                continue
            last = self._last_sent.get(m.mapping_id)
            if last:
                last_t, last_vals = last
                if m.min_interval_ms and (now-last_t)*1000 < m.min_interval_ms:
                    continue
                if m.deadband and last_vals and max(abs(float(a)-float(b)) for a,b in zip(keyvals,last_vals)) < m.deadband:
                    continue
            self._last_sent[m.mapping_id] = (now, tuple(keyvals))
            proposals.append({"mapping_id": m.mapping_id, "domain": m.domain, "service": service, "entity_id": m.entity_id, "data": payload, "mode": m.mode})
        return proposals

    def snapshot(self):
        return [m.snapshot() for m in self.mappings.values()]
