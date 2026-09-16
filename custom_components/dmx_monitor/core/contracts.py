"""HA-independent runtime contracts shared by protocol adapters and flows."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

@dataclass(frozen=True, slots=True)
class ProtocolObservation:
    protocol: str
    source: str | None = None
    interface: str | None = None
    kind: str = "telemetry"
    values: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=monotonic)

@dataclass(frozen=True, slots=True)
class ServiceAction:
    domain: str
    service: str
    data: dict[str, Any] = field(default_factory=dict)
    origin: str = "runtime"
    rate_limit_hz: float | None = None

@dataclass(frozen=True, slots=True)
class DriverStatus:
    key: str
    state: str
    category: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
