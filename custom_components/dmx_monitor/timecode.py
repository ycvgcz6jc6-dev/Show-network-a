"""Art-Net ArtTimeCode (opcode 0x9700) passive observer.

lighting_receiver.py forwards *every* raw Art-Net packet to the configured
``on_timecode`` callback (it does not pre-filter by opcode, since it already
needs to inspect the packet for ArtDMX separately) -- so this module's
``observe()`` must itself recognize and ignore anything that isn't a valid
ArtTimeCode packet, which will in practice be the overwhelming majority of
traffic (ArtDMX). This is purely a receiver: it never transmits timecode.
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field

_ART_NET_ID = b"Art-Net\x00"
_OP_TIME_CODE = 0x9700
_MIN_PACKET_LEN = 19

_FRAME_TYPES = {
    0: "24fps (Film)",
    1: "25fps (EBU)",
    2: "29.97fps (Drop-Frame)",
    3: "30fps (SMPTE)",
}


@dataclass(frozen=True)
class TimecodeFrame:
    hours: int
    minutes: int
    seconds: int
    frames: int
    frame_type: str
    source: str
    timestamp: float = field(default_factory=time.time)

    @property
    def formatted(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}:{self.frames:02d}"


class TimecodeMonitor:
    """Tracks the most recently observed ArtTimeCode frame per source."""

    def __init__(self, stale_after_s: float = 2.0) -> None:
        self.stale_after_s = float(stale_after_s)
        self.last: TimecodeFrame | None = None
        self.packets = 0
        self.parse_errors = 0
        self.sources: set[str] = set()

    @staticmethod
    def _parse(data: bytes, source: str) -> TimecodeFrame | None:
        if len(data) < _MIN_PACKET_LEN or data[:8] != _ART_NET_ID:
            return None
        opcode = struct.unpack("<H", data[8:10])[0]
        if opcode != _OP_TIME_CODE:
            return None
        frames, seconds, minutes, hours, type_byte = data[14], data[15], data[16], data[17], data[18]
        return TimecodeFrame(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            frames=frames,
            frame_type=_FRAME_TYPES.get(type_byte, f"unknown(0x{type_byte:02x})"),
            source=source,
        )

    def observe(self, data: bytes, source: str) -> None:
        """Called for every raw Art-Net packet; silently ignores non-timecode ones."""
        try:
            frame = self._parse(bytes(data), source)
        except (struct.error, IndexError):
            self.parse_errors += 1
            return
        if frame is None:
            return  # Not an ArtTimeCode packet (almost always ArtDMX) -- not an error.
        self.packets += 1
        self.sources.add(source)
        self.last = frame

    def snapshot(self) -> dict:
        now = time.time()
        last = self.last
        age = None if last is None else max(0.0, now - last.timestamp)
        return {
            "timecode_packets": self.packets,
            "timecode_parse_errors": self.parse_errors,
            "timecode_sources": sorted(self.sources),
            "timecode_last_source": last.source if last else None,
            "timecode_last_type": last.frame_type if last else None,
            "timecode_hh": last.hours if last else None,
            "timecode_mm": last.minutes if last else None,
            "timecode_ss": last.seconds if last else None,
            "timecode_ff": last.frames if last else None,
            "timecode_formatted": last.formatted if last else None,
            "timecode_age_s": None if age is None else round(age, 3),
            "timecode_fresh": age is not None and age < self.stale_after_s,
        }
