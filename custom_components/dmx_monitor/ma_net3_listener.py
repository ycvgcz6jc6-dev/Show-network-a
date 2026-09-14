"""Passive MA-Net3 multicast listener.

Receive-only: the integration never sends MA-Net3/session/control payloads.
Joining multicast groups only asks the OS to receive traffic for them.
"""
from __future__ import annotations
import asyncio
import socket
from dataclasses import dataclass
from time import monotonic, time

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
        self.state = "starting"
        self.last_error: str | None = None
        self.bound_endpoint: str | None = None
        self.joined_groups: list[str] = []
        self.join_errors: list[str] = []
        self.last_source: str | None = None
        self.last_packet_epoch: float | None = None

    async def start(self):
        if self.transports:
            return
        loop = asyncio.get_running_loop()
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.port))
            self.bound_endpoint = f"{sock.getsockname()[0]}:{sock.getsockname()[1]}"
            self.joined_groups = []
            self.join_errors = []
            for group in self.groups:
                membership = socket.inet_aton(group) + socket.inet_aton(self.interface_ip)
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                    self.joined_groups.append(group)
                except OSError as err:
                    self.join_errors.append(f"{group}: {type(err).__name__}: {err}")
                    raise
            sock.setblocking(False)
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _Protocol(self, "multi"), sock=sock
            )
            self.transports.append(transport)
            self.state = "listening"
            self.last_error = None
        except Exception as err:
            self.state = "error"
            self.last_error = f"{type(err).__name__}: {err}"
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
        self.last_packet_epoch = time()
        self.last_source = source
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
            "diagnostics": {
                "state": self.state, "interface": self.interface_ip, "port": self.port,
                "bound_endpoint": self.bound_endpoint, "configured_groups": list(self.groups),
                "joined_groups": list(self.joined_groups), "join_errors": list(self.join_errors),
                "last_error": self.last_error, "last_source": self.last_source,
                "last_packet_epoch": self.last_packet_epoch,
            },
        }

class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, owner: MANet3Listener, group: str):
        self.owner = owner
        self.group = group
    def datagram_received(self, data, addr):
        self.owner.record(data, addr, self.group)
