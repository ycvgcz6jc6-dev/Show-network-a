"""Small HA-independent runtime observability helpers."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

@dataclass
class RuntimeMetrics:
    received: int = 0
    processed: int = 0
    dropped: int = 0
    coalesced: int = 0
    errors: int = 0
    started_at: float = field(default_factory=monotonic)

    def record(self, **counts: int) -> None:
        for key, value in counts.items():
            if hasattr(self, key):
                setattr(self, key, max(0, int(getattr(self, key)) + int(value)))

    def snapshot(self) -> dict[str, Any]:
        return {
            "received": self.received, "processed": self.processed,
            "dropped": self.dropped, "coalesced": self.coalesced,
            "errors": self.errors,
            "uptime_s": round(max(0.0, monotonic() - self.started_at), 3),
        }
