"""Passive ST 2110/RTP observation helpers.

No NMOS registration, routing, subscription or media transmission is performed.
The inspector only classifies RTP-like UDP observations supplied by a caller.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import time

@dataclass
class ST2110Observation:
    packets: int = 0
    rtp_packets: int = 0
    sources: int = 0
    last_source: str | None = None
    last_payload_type: int | None = None
    last_sequence: int | None = None
    last_timestamp: int | None = None
    last_size: int = 0
    last_timestamp_seen: float = 0.0

class ST2110PassiveInspector:
    """Classify observed RTP packets without joining or controlling media flows."""
    def __init__(self) -> None:
        self.observation = ST2110Observation()
        self._sources: Counter[str] = Counter()
        self._payload_types: Counter[int] = Counter()

    @staticmethod
    def parse_rtp_header(packet: bytes) -> dict | None:
        if len(packet) < 12:
            return None
        b0, b1 = packet[0], packet[1]
        version = b0 >> 6
        if version != 2:
            return None
        cc = b0 & 0x0F
        header_len = 12 + 4 * cc
        if len(packet) < header_len:
            return None
        return {
            "version": version,
            "marker": bool(b1 & 0x80),
            "payload_type": b1 & 0x7F,
            "sequence": int.from_bytes(packet[2:4], "big"),
            "timestamp": int.from_bytes(packet[4:8], "big"),
            "ssrc": int.from_bytes(packet[8:12], "big"),
            "header_length": header_len,
        }

    def observe_udp(self, source: str | None, packet: bytes) -> bool:
        self.observation.packets += 1
        parsed = self.parse_rtp_header(packet)
        if not parsed:
            return False
        self.observation.rtp_packets += 1
        self.observation.last_source = source
        self.observation.last_payload_type = parsed["payload_type"]
        self.observation.last_sequence = parsed["sequence"]
        self.observation.last_timestamp = parsed["timestamp"]
        self.observation.last_size = len(packet)
        self.observation.last_timestamp_seen = time.time()
        if source:
            self._sources[source] += 1
        self._payload_types[parsed["payload_type"]] += 1
        self.observation.sources = len(self._sources)
        return True

    def snapshot(self) -> dict:
        return {
            "st2110_packets": self.observation.packets,
            "st2110_rtp_packets": self.observation.rtp_packets,
            "st2110_sources": self.observation.sources,
            "st2110_last_source": self.observation.last_source,
            "st2110_last_payload_type": self.observation.last_payload_type,
            "st2110_last_sequence": self.observation.last_sequence,
            "st2110_last_timestamp": self.observation.last_timestamp,
            "st2110_last_size": self.observation.last_size,
            "st2110_payload_types": dict(self._payload_types),
            "st2110_top_sources": self._sources.most_common(10),
            "st2110_last_seen": self.observation.last_timestamp_seen or None,
        }
