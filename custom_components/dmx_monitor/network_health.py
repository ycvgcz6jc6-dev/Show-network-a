"""Read-only network health aggregation for the Show Network integration."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from time import time

@dataclass
class NetworkObservation:
    interface: str
    timestamp: float = field(default_factory=time)
    multicast_groups: int = 0
    multicast_sources: int = 0
    vlan_id: int | None = None
    qos_markings: dict[str, int] = field(default_factory=dict)
    poe_ports: int = 0
    poe_power_w: float = 0.0
    errors: int = 0
    drops: int = 0
    packets: int = 0
    protocols: dict[str, int] = field(default_factory=dict)

class NetworkHealth:
    """Aggregates observed network health without changing configuration."""
    def __init__(self, stale_after_s: float = 15.0) -> None:
        self.observations: list[NetworkObservation] = []
        self.stale_after_s = float(stale_after_s)

    def record(self, observation: NetworkObservation) -> None:
        self.observations.append(observation)
        if len(self.observations) > 1000:
            self.observations = self.observations[-1000:]

    @property
    def latest(self) -> NetworkObservation | None:
        return self.observations[-1] if self.observations else None

    def observe_packet(self, interface: str, protocol: str) -> None:
        latest = self.latest
        if latest is None or latest.interface != interface:
            latest = NetworkObservation(interface=interface)
            self.record(latest)
        latest.timestamp = time()
        latest.packets += 1
        latest.protocols[protocol] = latest.protocols.get(protocol, 0) + 1

    def snapshot(self, now: float | None = None) -> dict:
        now = time() if now is None else now
        by_interface = {}
        for item in self.observations:
            by_interface[item.interface] = item
        interfaces = []
        for item in by_interface.values():
            age = max(0.0, now - item.timestamp)
            interfaces.append({**asdict(item), "age_s": round(age, 3), "health": "up" if age <= self.stale_after_s else "stale"})
        return {
            "interfaces": interfaces,
            "interfaces_up": sum(i["health"] == "up" for i in interfaces),
            "interfaces_stale": sum(i["health"] == "stale" for i in interfaces),
            "packets_observed": sum(i["packets"] for i in interfaces),
            "protocols": sorted({p for i in interfaces for p in i["protocols"]}),
        }
