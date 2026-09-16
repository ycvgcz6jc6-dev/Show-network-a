"""Chaos-testing state tracker and network capacity estimator.

ChaosSimulator does not inject any real fault on the network: it only
records that an operator has asked the UI to *pretend* a fault is
happening (e.g. "simulate signal loss"), so other read-only monitoring code
can be exercised without physically unplugging anything. It never
suppresses real packets.

capacity_snapshot() is an *estimate*, clearly labelled as such: DMX
bandwidth is derived from observed packet rate and channel count (not a
wire measurement), while Dante/camera/ST2110/other figures are whatever the
operator entered via set_capacity_config -- never something this integration
measured itself.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Rough per-packet overhead (UDP/IP/Ethernet headers plus protocol framing)
# added on top of the DMX payload for a bandwidth *estimate*. Real overhead
# varies slightly by protocol (sACN root/framing/DMP layers vs. Art-Net's
# smaller header) -- this is a deliberately simple, conservative constant,
# not a precise measurement.
_ESTIMATED_HEADER_OVERHEAD_BYTES = 60


@dataclass
class ChaosEvent:
    key: str
    kind: str
    description: str
    started_at: float = field(default_factory=time.time)


class ChaosSimulator:
    """Tracks which fault simulations are currently 'active' for the UI."""

    def __init__(self) -> None:
        self.active: dict[str, ChaosEvent] = {}

    def start(self, key: str, kind: str, description: str) -> None:
        self.active[key] = ChaosEvent(key=key, kind=kind, description=description)

    def stop(self, key: str | None = None) -> None:
        """Stop one simulation by key, or every active simulation if key is None."""
        if key is None:
            self.active.clear()
        else:
            self.active.pop(key, None)

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        events = [
            {
                "key": e.key,
                "kind": e.kind,
                "description": e.description,
                "active_for_s": round(now - e.started_at, 1),
            }
            for e in self.active.values()
        ]
        return {
            "chaos_active": bool(events),
            "chaos_events": events,
            "chaos_note": "Simulated state only; no real network packets are suppressed or altered.",
        }


def capacity_snapshot(
    dmx_universes: list[dict[str, Any]] | None,
    *,
    link_mbps: float = 1000.0,
    dante_mbps: float = 0.0,
    cameras_mbps: float = 0.0,
    st2110_mbps: float = 0.0,
    other_mbps: float = 0.0,
) -> dict[str, Any]:
    dmx_mbps = 0.0
    for item in dmx_universes or ():
        try:
            packet_rate = float(item.get("packet_rate") or 0.0)
            active_channels = int(item.get("active_channels") or 0)
        except (AttributeError, TypeError, ValueError):
            continue
        bytes_per_packet = active_channels + _ESTIMATED_HEADER_OVERHEAD_BYTES
        dmx_mbps += (bytes_per_packet * packet_rate * 8) / 1_000_000.0

    configured_mbps = float(dante_mbps) + float(cameras_mbps) + float(st2110_mbps) + float(other_mbps)
    total_mbps = dmx_mbps + configured_mbps
    usage_pct = (total_mbps / link_mbps * 100.0) if link_mbps > 0 else None

    return {
        "link_mbps": link_mbps,
        "estimated_dmx_mbps": round(dmx_mbps, 3),
        "configured_dante_mbps": dante_mbps,
        "configured_cameras_mbps": cameras_mbps,
        "configured_st2110_mbps": st2110_mbps,
        "configured_other_mbps": other_mbps,
        "estimated_total_mbps": round(total_mbps, 3),
        "estimated_usage_pct": None if usage_pct is None else round(usage_pct, 1),
        "over_capacity": usage_pct is not None and usage_pct > 100.0,
        "note": (
            "DMX figure is estimated from observed packet rate and channel "
            "count, not a wire measurement. Dante/camera/ST2110/other figures "
            "are the operator's own configured estimates, not measured traffic."
        ),
    }
