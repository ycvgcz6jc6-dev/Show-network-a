"""Receive-only IP tally monitor.

The listener deliberately implements only published TSL UMD receive semantics:
- UMD v5.0 display messages over UDP
- the legacy v3.1/v4 UDP prefix for simple tally on/off reception

It never transmits packets.  The Home Assistant surface is intentionally one
binary sensor: ON whenever a matching display has at least one active tally.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Callable, Iterable


TALLY_NAMES = ("right", "text", "left")
TALLY_COLORS = {0: "off", 1: "red", 2: "green", 3: "amber"}


@dataclass(frozen=True, slots=True)
class TallyObservation:
    protocol: str
    screen: int
    index: int
    text: str
    tally_values: tuple[int, ...]

    @property
    def on(self) -> bool:
        return any(value != 0 for value in self.tally_values)

    @property
    def colors(self) -> list[str]:
        return [TALLY_COLORS.get(value & 0x03, "unknown") for value in self.tally_values]


def parse_tsl_umd_v5(packet: bytes) -> list[TallyObservation]:
    """Parse one UDP UMD v5.0 packet.

    Invalid, screen-control, future-version and control-data messages are
    rejected/ignored conservatively rather than guessed.
    """
    if len(packet) < 6 or len(packet) > 2048:
        raise ValueError("invalid TSL UMD v5 packet length")
    pbc = int.from_bytes(packet[0:2], "little")
    # PBC is the byte count following the PBC field itself.
    if pbc != len(packet) - 2:
        raise ValueError("TSL UMD v5 PBC mismatch")
    version = packet[2]
    flags = packet[3]
    if version != 0:
        raise ValueError("unsupported TSL UMD v5 minor version")
    if flags & 0xFC:
        raise ValueError("reserved TSL UMD v5 flags are set")
    if flags & 0x02:
        return []  # SCONTROL is explicitly undefined in v5.0.
    unicode_text = bool(flags & 0x01)
    screen = int.from_bytes(packet[4:6], "little")
    offset = 6
    out: list[TallyObservation] = []
    while offset < len(packet):
        if len(packet) - offset < 6:
            raise ValueError("truncated TSL UMD v5 DMSG")
        index = int.from_bytes(packet[offset:offset + 2], "little")
        control = int.from_bytes(packet[offset + 2:offset + 4], "little")
        length = int.from_bytes(packet[offset + 4:offset + 6], "little")
        offset += 6
        if control & 0x8000:
            # Control-data layout is undefined by the published v5.0 spec.
            if length > len(packet) - offset:
                raise ValueError("truncated TSL UMD v5 control data")
            offset += length
            continue
        if length > len(packet) - offset:
            raise ValueError("truncated TSL UMD v5 text")
        raw_text = packet[offset:offset + length]
        offset += length
        encoding = "utf-16-le" if unicode_text else "ascii"
        try:
            text = raw_text.decode(encoding, errors="replace").rstrip("\x00 ")
        except UnicodeDecodeError:
            text = ""
        # Published bit order: RH 0..1, Text 2..3, LH 4..5.
        tallies = (control & 0x03, (control >> 2) & 0x03, (control >> 4) & 0x03)
        out.append(TallyObservation("TSL UMD v5", screen, index, text, tallies))
    return out


def parse_tsl_umd_legacy(packet: bytes) -> list[TallyObservation]:
    """Parse the v3.1-compatible prefix used by TSL UMD v3.1/v4 UDP."""
    if len(packet) < 18:
        raise ValueError("TSL UMD legacy packet too short")
    header = packet[0]
    if not (0x80 <= header <= 0xFE):
        raise ValueError("invalid TSL UMD legacy header")
    control = packet[1]
    # Command data is not a tally display update.
    if control & 0x40:
        return []
    address = header - 0x80
    raw_text = packet[2:18]
    text = raw_text.decode("ascii", errors="replace").rstrip("\x00 ")
    tallies = tuple(1 if control & (1 << bit) else 0 for bit in range(4))
    protocol = "TSL UMD v4/v3.1" if len(packet) > 18 else "TSL UMD v3.1"
    return [TallyObservation(protocol, 0, address, text, tallies)]


def parse_tally_packet(packet: bytes) -> list[TallyObservation]:
    """Auto-detect supported TSL UMD packet forms without accepting garbage."""
    try:
        return parse_tsl_umd_v5(packet)
    except ValueError:
        return parse_tsl_umd_legacy(packet)


class _TallyDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, owner: "TallyIPReceiver") -> None:
        self.owner = owner

    def datagram_received(self, data: bytes, addr) -> None:
        self.owner._datagram_received(data, addr)

    def error_received(self, exc: Exception) -> None:
        self.owner.last_error = str(exc)
        self.owner._publish()


class TallyIPReceiver:
    """Small UDP receiver exposing one filtered tally state."""

    def __init__(
        self,
        interface: str,
        port: int,
        callback: Callable[[dict], None],
        *,
        screen: int = -1,
        index: int = -1,
        stale_timeout: float = 10.0,
    ) -> None:
        self.interface = str(interface or "0.0.0.0")
        self.port = int(port)
        self.screen = int(screen)
        self.index = int(index)
        self.stale_timeout = max(0.5, float(stale_timeout))
        self.callback = callback
        self.transport: asyncio.DatagramTransport | None = None
        self.messages = 0
        self.invalid_packets = 0
        self.on = False
        self.protocol: str | None = None
        self.text = ""
        self.colors: list[str] = []
        self.last_source: str | None = None
        self.last_seen: float | None = None
        self.last_error: str | None = None
        self._stale_handle: asyncio.TimerHandle | None = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _TallyDatagramProtocol(self),
            local_addr=(self.interface, self.port),
        )
        self.transport = transport
        self._publish()

    async def stop(self) -> None:
        if self._stale_handle is not None:
            self._stale_handle.cancel()
            self._stale_handle = None
        if self.transport is not None:
            self.transport.close()
            self.transport = None
        self.on = False
        self._publish()

    def _matches(self, obs: TallyObservation) -> bool:
        return (self.screen < 0 or obs.screen in (self.screen, 0xFFFF)) and (
            self.index < 0 or obs.index in (self.index, 0xFFFF)
        )

    def _datagram_received(self, data: bytes, addr) -> None:
        try:
            observations = parse_tally_packet(bytes(data))
        except ValueError as err:
            self.invalid_packets += 1
            self.last_error = str(err)
            self._publish()
            return
        matches = [obs for obs in observations if self._matches(obs)]
        if not matches:
            return
        self.messages += 1
        self.last_source = str(addr[0]) if addr else None
        self.last_seen = time.time()
        self.last_error = None
        self.on = any(obs.on for obs in matches)
        active = next((obs for obs in matches if obs.on), matches[-1])
        self.protocol = active.protocol
        self.text = active.text
        self.colors = active.colors
        self._arm_stale_timer()
        self._publish()

    def _arm_stale_timer(self) -> None:
        if self._stale_handle is not None:
            self._stale_handle.cancel()
        loop = asyncio.get_running_loop()
        self._stale_handle = loop.call_later(self.stale_timeout, self._expire)

    def _expire(self) -> None:
        self._stale_handle = None
        self.on = False
        self._publish()

    def snapshot(self) -> dict:
        age = None if self.last_seen is None else max(0.0, time.time() - self.last_seen)
        return {
            "enabled": True,
            "listening": self.transport is not None,
            "on": self.on,
            "interface": self.interface,
            "port": self.port,
            "screen_filter": self.screen,
            "index_filter": self.index,
            "stale_timeout_s": self.stale_timeout,
            "messages": self.messages,
            "invalid_packets": self.invalid_packets,
            "protocol": self.protocol,
            "text": self.text,
            "colors": list(self.colors),
            "last_source": self.last_source,
            "last_seen": self.last_seen,
            "age_s": round(age, 3) if age is not None else None,
            "last_error": self.last_error,
            "receive_only": True,
        }

    def _publish(self) -> None:
        self.callback(self.snapshot())
