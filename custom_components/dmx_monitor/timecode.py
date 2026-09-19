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
    def __init__(self):
        self.state = TimecodeState()
        self.packet_count = 0
        self._previous_seen = None
        self._interval_ms = None
        self._mtc_nibbles = {}
        self._mtc_piece_seen = {}
    def observe_artnet(self, data: bytes, source: str):
        parsed = parse_artnet_timecode(data)
        if not parsed: return False
        h,m,s,f,fps,kind = parsed
        now = monotonic()
        if self._previous_seen is not None:
            self._interval_ms = max(0.0, (now - self._previous_seen) * 1000.0)
        self._previous_seen = now
        self.packet_count += 1
        self.state = TimecodeState(h,m,s,f,fps,kind,source,now)
        self._transport = "Art-Net ArtTimeCode"
        self._evidence = "decoded ArtTimeCode packet"
        return True

    def observe_mtc(self, message):
        """Observe normalized MIDI quarter-frame and reconstruct MTC.

        A value is published only after all eight quarter-frame pieces have
        been observed. This is receive-only and uses the already configured
        MIDI input.
        """
        if getattr(message, "message_type", "") != "quarter_frame" or len(getattr(message, "data", ())) < 2:
            return False
        piece, value = int(message.data[0]), int(message.data[1]) & 0x0F
        if not 0 <= piece <= 7:
            return False
        now = monotonic()
        # Never combine a quarter-frame received long ago with a new cycle.
        # MTC may arrive forward or reverse, so freshness is validated instead
        # of imposing one sequence direction.
        stale = [k for k, ts in self._mtc_piece_seen.items() if now - ts > 1.0]
        for k in stale:
            self._mtc_piece_seen.pop(k, None); self._mtc_nibbles.pop(k, None)
        self._mtc_nibbles[piece] = value
        self._mtc_piece_seen[piece] = now
        if len(self._mtc_nibbles) < 8:
            return False
        n=dict(self._mtc_nibbles)
        frames=n[0] | ((n[1] & 0x1) << 4)
        seconds=n[2] | ((n[3] & 0x3) << 4)
        minutes=n[4] | ((n[5] & 0x3) << 4)
        hours=n[6] | ((n[7] & 0x1) << 4)
        rate=(n[7] >> 1) & 0x3
        fps={0:24.0,1:25.0,2:29.97,3:30.0}.get(rate,25.0)
        kind={0:"film",1:"EBU",2:"DF",3:"SMPTE"}.get(rate,"unknown")
        # Consume the coherent set: the next publication requires eight fresh
        # pieces again and cannot silently reuse stale nibbles.
        self._mtc_nibbles.clear(); self._mtc_piece_seen.clear()
        if self._previous_seen is not None:
            self._interval_ms=max(0.0,(now-self._previous_seen)*1000.0)
        self._previous_seen=now; self.packet_count += 1
        self.state=TimecodeState(hours,minutes,seconds,frames,fps,kind,getattr(message,"source",None),now)
        self._transport="MIDI Time Code (MTC quarter-frame)"
        self._evidence="decoded complete 8-piece MTC quarter-frame set"
        return True

    def snapshot(self):
        s = self.state
        age = None if s.last_seen is None else max(0.0, monotonic() - s.last_seen)
        locked = age is not None and age <= 2.0
        return {
            "text": s.text if s.last_seen is not None else "--:--:--:--",
            "hours": s.hours, "minutes": s.minutes, "seconds": s.seconds, "frames": s.frames,
            "fps": s.fps, "type": s.type, "source": s.source,
            "drop_frame": s.type == "DF", "last_seen": s.last_seen,
            "age_s": round(age, 3) if age is not None else None,
            "locked": locked, "status": "locked" if locked else ("lost" if s.last_seen is not None else "waiting"),
            "transport": getattr(self, "_transport", "Art-Net ArtTimeCode"),
            "packet_count": self.packet_count,
            "last_packet_interval_ms": round(self._interval_ms, 2) if self._interval_ms is not None else None,
            "freshness": "fresh" if locked else ("stale" if s.last_seen is not None else "unknown"),
            "evidence": getattr(self, "_evidence", "decoded ArtTimeCode packet"),
        }
