"""Low-cost host resource telemetry for Show Network.

The readings describe the Home Assistant host/container running the integration.
They are intentionally read-only and use non-blocking psutil calls.
"""
from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass(frozen=True, slots=True)
class HostMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    memory_total_bytes: int

    def snapshot(self) -> dict[str, float | int]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_bytes": self.memory_used_bytes,
            "memory_total_bytes": self.memory_total_bytes,
        }


def snapshot() -> HostMetrics:
    """Read current host metrics without sleeping or blocking the event loop."""
    vm = psutil.virtual_memory()
    return HostMetrics(
        cpu_percent=float(psutil.cpu_percent(interval=None)),
        memory_percent=float(vm.percent),
        memory_used_bytes=int(vm.used),
        memory_total_bytes=int(vm.total),
    )
