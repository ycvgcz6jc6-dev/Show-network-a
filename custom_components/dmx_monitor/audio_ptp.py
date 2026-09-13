"""Passive PTP/audio-network observer for the AUDIO domain.

This module never transmits PTP, Dante, AES67 or ST2110 packets. It only
binds UDP sockets for reception and records lightweight packet metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import logging
import socket
import struct
import time

_LOGGER = logging.getLogger(__name__)
PTP_EVENT_PORT = 319
PTP_GENERAL_PORT = 320

@dataclass(frozen=True)
class PTPObservation:
    source: str
    port: int
    message_type: int | None
    version: int | None
    domain: int | None
    length: int
    timestamp: float

class PTPMonitor:
    """Receive-only PTP envelope observer."""
    def __init__(self, interface: str = "0.0.0.0") -> None:
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.ports: set[int] = set()
        self.last: PTPObservation | None = None
        self.event_packets = 0
        self.general_packets = 0
        self._last_time: float | None = None
        self.inter_arrival_ms = 0.0
        self.jitter_ms = 0.0
        self.announce_packets = 0
        self.sync_packets = 0
        self.follow_up_packets = 0
        self.delay_packets = 0
        self.last_source_identity: str | None = None
        self.last_grandmaster_identity: str | None = None
        self.grandmaster_priority1: int | None = None
        self.grandmaster_clock_class: int | None = None
        self.grandmaster_accuracy: int | None = None
        self.grandmaster_priority2: int | None = None
        self._tasks: list[asyncio.Task] = []
        self._sockets: list[socket.socket] = []

    async def start(self) -> None:
        if self._tasks:
            return
        try:
            for port in (PTP_EVENT_PORT, PTP_GENERAL_PORT):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.bind((self.interface, port))
                    sock.setblocking(False)
                    self._sockets.append(sock)
                    self._tasks.append(asyncio.create_task(self._receive(sock, port), name=f"show-network-ptp-{port}"))
                except Exception:
                    sock.close()
                    raise
        except Exception:
            await self.stop()
            raise

    async def _receive(self, sock: socket.socket, port: int) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                data, addr = await loop.sock_recvfrom(sock, 2048)
            except asyncio.CancelledError:
                return
            except OSError:
                return
            if not data:
                continue
            now = time.time()
            msg_type = data[0] & 0x0F if len(data) >= 1 else None
            version = data[1] & 0x0F if len(data) >= 2 else None
            domain = data[4] if len(data) >= 5 else None
            if self._last_time is not None:
                inter = (now - self._last_time) * 1000.0
                previous = self.inter_arrival_ms
                self.inter_arrival_ms = inter
                self.jitter_ms = abs(inter - previous) if previous else 0.0
            self._last_time = now
            if msg_type == 0: self.sync_packets += 1
            elif msg_type == 8: self.follow_up_packets += 1
            elif msg_type in (1, 9): self.delay_packets += 1
            elif msg_type == 11:
                self.announce_packets += 1
                if len(data) >= 64:
                    self.last_source_identity = data[20:28].hex()
                    self.grandmaster_priority1 = data[47]
                    self.grandmaster_clock_class = data[48]
                    self.grandmaster_accuracy = data[49]
                    self.grandmaster_priority2 = data[52]
                    self.last_grandmaster_identity = data[53:61].hex()
            self.packets += 1
            if port == PTP_EVENT_PORT:
                self.event_packets += 1
            else:
                self.general_packets += 1
            self.sources.add(addr[0])
            self.ports.add(port)
            self.last = PTPObservation(addr[0], port, msg_type, version, domain, len(data), now)

    def snapshot(self) -> dict:
        last = self.last
        return {
            "ptp_packets": self.packets,
            "ptp_sources": len(self.sources),
            "ptp_event_packets": self.event_packets,
            "ptp_general_packets": self.general_packets,
            "ptp_ports": sorted(self.ports),
            "ptp_last_source": last.source if last else None,
            "ptp_last_message_type": last.message_type if last else None,
            "ptp_last_version": last.version if last else None,
            "ptp_last_domain": last.domain if last else None,
            "ptp_last_length": last.length if last else None,
            "ptp_last_seen": last.timestamp if last else None,
            "ptp_inter_arrival_ms": round(self.inter_arrival_ms, 3),
            "ptp_jitter_ms": round(self.jitter_ms, 3),
            "ptp_announce_packets": self.announce_packets,
            "ptp_sync_packets": self.sync_packets,
            "ptp_follow_up_packets": self.follow_up_packets,
            "ptp_delay_packets": self.delay_packets,
            "ptp_last_source_identity": self.last_source_identity,
            "ptp_grandmaster_identity": self.last_grandmaster_identity,
            "ptp_grandmaster_priority1": self.grandmaster_priority1,
            "ptp_grandmaster_clock_class": self.grandmaster_clock_class,
            "ptp_grandmaster_accuracy": self.grandmaster_accuracy,
            "ptp_grandmaster_priority2": self.grandmaster_priority2,
        }

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        for sock in self._sockets:
            try:
                sock.close()
            except OSError:
                pass
        self._sockets.clear()
