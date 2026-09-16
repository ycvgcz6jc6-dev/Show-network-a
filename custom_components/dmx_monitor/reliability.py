"""Show Network reliability helpers: chaos simulation and bandwidth prediction."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

@dataclass
class ChaosState:
    active: bool = False
    target: str | None = None
    mode: str | None = None
    started_at: str | None = None
    detail: str | None = None

class ChaosSimulator:
    """Never changes the physical network; only injects logical test state."""
    def __init__(self) -> None:
        self.state = ChaosState()

    def start(self, target: str, mode: str, detail: str = "") -> dict[str, Any]:
        self.state = ChaosState(True, target, mode, datetime.now(timezone.utc).isoformat(), detail or None)
        return asdict(self.state)

    def stop(self) -> dict[str, Any]:
        self.state = ChaosState()
        return asdict(self.state)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self.state)

def estimate_dmx_mbps(universes: list[dict[str, Any]], packet_bytes: int = 700) -> float:
    total = 0.0
    for u in universes:
        rate = float(u.get("packet_rate") or 0)
        total += rate * packet_bytes * 8 / 1_000_000
    return total

def capacity_snapshot(universes: list[dict[str, Any]], dante_mbps: float = 0.0,
                      cameras_mbps: float = 0.0, st2110_mbps: float = 0.0,
                      other_mbps: float = 0.0, link_mbps: float = 1000.0) -> dict[str, Any]:
    dmx = estimate_dmx_mbps(universes)
    artnet = sum(estimate_dmx_mbps([u]) for u in universes if str(u.get("protocol", "")).lower() == "art-net")
    sacn = sum(estimate_dmx_mbps([u]) for u in universes if str(u.get("protocol", "")).lower() == "sacn")
    total = dmx + float(dante_mbps) + float(cameras_mbps) + float(st2110_mbps) + float(other_mbps)
    pct = (total / link_mbps * 100) if link_mbps > 0 else 0
    status = "ok" if pct < 75 else "warning" if pct < 90 else "critical"
    return {"link_mbps": round(link_mbps, 2), "dmx_mbps": round(dmx, 2),
            "sacn_mbps": round(sacn, 2), "artnet_mbps": round(artnet, 2),
            "dante_mbps": round(float(dante_mbps), 2), "cameras_mbps": round(float(cameras_mbps), 2),
            "st2110_mbps": round(float(st2110_mbps), 2), "other_mbps": round(float(other_mbps), 2),
            "total_mbps": round(total, 2), "utilization_pct": round(pct, 1),
            "headroom_mbps": round(max(0.0, link_mbps - total), 2), "status": status}
