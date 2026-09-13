"""Passive MA-Net3 multicast listener.

Receive-only: the integration never sends MA-Net3/session/control payloads.
Joining multicast groups only asks the OS to receive traffic for them.
"""
from __future__ import annotations
import asyncio
import socket
from dataclasses import dataclass
from time import monotonic

MA_NET3_PORT = 30020
DEFAULT_GROUPS = ("236.4.1.0", "236.4.1.1", "236.4.1.2", "236.4.1.3", "236.4.1.4")

@dataclass(frozen=True)
class MAObservation:
    source_ip: str
    destination_group: str
    size: int
    received_at: float

class MANet3Listener:
    def __init__(self, interface_ip: str, groups=DEFAULT_GROUPS, port=MA_NET3_PORT):
        self.interface_ip = interface_ip
        self.groups = tuple(groups)
        self.port = port
        self.transports = []
        self.observations: list[MAObservation] = []
        self.packet_count = 0
        self.last_seen: float | None = None
        self.bytes = 0
        self.sources: set[str] = set()
        self.groups_seen: set[str] = set()

    async def start(self):
        if self.transports:
            return
        loop = asyncio.get_running_loop()
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.port))
            for group in self.groups:
                membership = socket.inet_aton(group) + socket.inet_aton(self.interface_ip)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            sock.setblocking(False)
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _Protocol(self, "multi"), sock=sock
            )
            self.transports.append(transport)
        except Exception:
            try:
                if sock is not None:
                    sock.close()
            except Exception:
                pass
            await self.stop()
            raise

    async def stop(self):
        for transport in self.transports:
            transport.close()
        self.transports.clear()

    def record(self, data: bytes, addr, group: str):
        now = monotonic()
        source = addr[0]
        self.packet_count += 1
        self.bytes += len(data)
        self.last_seen = now
        self.sources.add(source)
        self.groups_seen.add(group)
        self.observations.append(MAObservation(source, group, len(data), now))
        if len(self.observations) > 250:
            del self.observations[:-250]

    def snapshot(self) -> dict:
        return {
            "packets": self.packet_count,
            "bytes": self.bytes,
            "sources": len(self.sources),
            "groups": len(self.groups_seen),
            "last_seen": self.last_seen,
            "observations": list(self.observations[-50:]),
        }

class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, owner: MANet3Listener, group: str):
        self.owner = owner
        self.group = group
    def datagram_received(self, data, addr):
        self.owner.record(data, addr, self.group)
