"""Conservative passive Dante endpoint inventory.

No queries or control packets are sent. Inventory is built only from observed
mDNS/DNS-SD payloads and source addresses. Names are treated as hints, not
authenticated device identity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import time

@dataclass
class DanteEndpoint:
    source: str
    first_seen: float
    last_seen: float
    packets: int = 0
    services: set[str] = field(default_factory=set)
    markers: set[str] = field(default_factory=set)

class DanteInventory:
    def __init__(self) -> None:
        self.endpoints: dict[str, DanteEndpoint] = {}

    def observe(self, source: str, payload: bytes) -> None:
        now=time.time(); item=self.endpoints.get(source)
        if item is None:
            item=DanteEndpoint(source, now, now); self.endpoints[source]=item
        item.last_seen=now; item.packets += 1
        lower=payload.lower()
        for marker in (b"_dante", b"_netaudio", b"audinate", b"dante"):
            if marker in lower: item.markers.add(marker.decode())
        for service in (b"_http._tcp", b"_https._tcp", b"_netaudio-arc._udp", b"_netaudio-dante._udp"):
            if service in lower: item.services.add(service.decode())

    def snapshot(self) -> dict:
        rows=[]
        for e in sorted(self.endpoints.values(), key=lambda x:x.source):
            rows.append({"source":e.source,"packets":e.packets,"services":sorted(e.services),"markers":sorted(e.markers),"last_seen":e.last_seen})
        return {"dante_endpoints":len(rows),"dante_inventory":rows}
