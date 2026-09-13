"""Small passive Art-Net TimeCode decoder.

This observes Art-Net TimeCode packets on the existing Art-Net socket; it does
not transmit timecode and does not open a second UDP/6454 listener.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic

@dataclass
class TimecodeState:
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    frames: int = 0
    fps: float = 25.0
    type: str = "film"
    source: str | None = None
    last_seen: float | None = None

    @property
    def text(self):
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}:{self.frames:02d}"

def parse_artnet_timecode(data: bytes):
    if len(data) < 19 or data[:8] != b"Art-Net\0": return None
    opcode = int.from_bytes(data[8:10], "little")
    if opcode != 0x9700: return None
    # ArtTimeCode: frames, seconds, minutes, hours, type at offsets 14..18.
    frames, seconds, minutes, hours, tc_type = data[14:19]
    fps = {0: 24.0, 1: 25.0, 2: 29.97, 3: 30.0}.get(tc_type, 25.0)
    names = {0: "film", 1: "EBU", 2: "DF", 3: "SMPTE"}
    return hours, minutes, seconds, frames, fps, names.get(tc_type, "unknown")

class TimecodeMonitor:
    def __init__(self): self.state = TimecodeState()
    def observe_artnet(self, data: bytes, source: str):
        parsed = parse_artnet_timecode(data)
        if not parsed: return False
        h,m,s,f,fps,kind = parsed
        self.state = TimecodeState(h,m,s,f,fps,kind,source,monotonic())
        return True
    def snapshot(self):
        s=self.state
        return {"text":s.text,"hours":s.hours,"minutes":s.minutes,"seconds":s.seconds,"frames":s.frames,"fps":s.fps,"type":s.type,"source":s.source,"last_seen":s.last_seen}
