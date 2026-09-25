"""Adaptive, low-overhead runtime performance policy.

The policy protects Home Assistant by reducing non-critical polling/UI work
before touching protocol reception or safety/watchdog paths.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PerformanceDecision:
    level: str
    telemetry_interval_s: float
    discovery_enabled: bool
    secondary_polling: bool

class AdaptivePerformance:
    """Choose conservative runtime settings from host CPU/RAM pressure."""
    def __init__(self, profile: str = "auto") -> None:
        self.profile = str(profile or "auto").lower()

    def decide(self, cpu_percent: float, memory_percent: float) -> PerformanceDecision:
        cpu = max(0.0, min(100.0, float(cpu_percent)))
        mem = max(0.0, min(100.0, float(memory_percent)))
        pressure = max(cpu, mem)
        if self.profile != "auto":
            return self._fixed(self.profile)
        if pressure >= 85:
            return PerformanceDecision("protection", 15.0, False, False)
        if pressure >= 70:
            return PerformanceDecision("economy", 10.0, False, True)
        if pressure >= 50:
            return PerformanceDecision("optimized", 7.0, True, True)
        return PerformanceDecision("normal", 5.0, True, True)

    @staticmethod
    def _fixed(profile: str) -> PerformanceDecision:
        return {
            "minimal": PerformanceDecision("minimal", 10.0, False, True),
            "standard": PerformanceDecision("standard", 5.0, True, True),
            "full": PerformanceDecision("full", 2.0, True, True),
        }.get(profile, PerformanceDecision("normal", 5.0, True, True))
