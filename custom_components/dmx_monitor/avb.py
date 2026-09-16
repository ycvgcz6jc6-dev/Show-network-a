"""Passive AVB/gPTP network observations. No AVB control or stream subscription."""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import socket, time

AVTP_ETHERTYPE = 0x22F0
GPTP_UDP_PORTS = (319, 320)

@dataclass
class AvbObservation:
    packets: int = 0
    last_source: str | None = None
    last_size: int = 0
    last_timestamp: float = 0.0
    ethertype_packets: int = 0

class AvbPassiveInspector:
    def __init__(self) -> None:
        self.observation = AvbObservation()
        self.sources = Counter()

    def observe_avtp(self, source: str | None, size: int) -> None:
        self.observation.packets += 1
        self.observation.ethertype_packets += 1
        self.observation.last_source = source
        self.observation.last_size = size
        self.observation.last_timestamp = time.time()
        if source: self.sources[source] += 1

    def snapshot(self) -> dict:
        return {"packets": self.observation.packets, "sources": len(self.sources), "top_sources": self.sources.most_common(10), "last_source": self.observation.last_source, "last_size": self.observation.last_size, "last_timestamp": self.observation.last_timestamp, "avb_last_seen": self.observation.last_timestamp or None}
