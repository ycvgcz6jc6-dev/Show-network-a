"""Passive Dante network observer.

This module is intentionally receive-only. It observes mDNS/DNS-SD traffic and
Dante-specific monitoring traffic, but never sends discovery, routing, clocking,
or audio-control packets.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import socket
import struct
import time

from .dante_inventory import DanteInventory

_LOGGER = logging.getLogger(__name__)
MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
DANTE_MONITOR_GROUPS = ("224.0.0.230", "224.0.0.231", "224.0.0.232", "224.0.0.233")
DANTE_MONITOR_PORTS = tuple(range(8700, 8709))
DANTE_SETUP_PORT = 4455

@dataclass(frozen=True)
class DanteObservation:
    source: str
    port: int
    kind: str
    length: int
    timestamp: float

class DanteMonitor:
    """Observe Dante-related network traffic without transmitting packets."""
    def __init__(self, interface: str = "0.0.0.0") -> None:
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.mdns_packets = 0
        self.dante_mdns_packets = 0
        self.monitor_packets = 0
        self.setup_packets = 0
        self.ports: set[int] = set()
        self.last: DanteObservation | None = None
        self.source_stats: dict[str, dict] = {}
        self._tasks: list[asyncio.Task] = []
        self._sockets: list[socket.socket] = []
        self.inventory = DanteInventory()

    def _make_multicast_socket(self, group: str, port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        iface = socket.inet_aton(self.interface) if self.interface != "0.0.0.0" else socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(group), iface))
        sock.setblocking(False)
        return sock

    async def start(self) -> None:
        if self._tasks:
            return
        try:
            # One socket per UDP port joins all monitor groups.  The previous
            # topology could create 36 monitor sockets/tasks; this keeps the
            # same receive coverage with only one task per port.
            sock = self._make_multicast_socket(MDNS_GROUP, MDNS_PORT)
            self._sockets.append(sock)
            self._tasks.append(asyncio.create_task(self._receive(sock, MDNS_PORT, "mdns"), name="show-network-dante-mdns"))
            for port in DANTE_MONITOR_PORTS:
                sock = self._make_monitor_socket(port)
                self._sockets.append(sock)
                self._tasks.append(asyncio.create_task(self._receive(sock, port, "monitor"), name=f"show-network-dante-{port}"))
        except Exception:
            await self.stop()
            raise

    def _make_monitor_socket(self, port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
            iface = socket.inet_aton(self.interface) if self.interface != "0.0.0.0" else socket.inet_aton("0.0.0.0")
            for group in DANTE_MONITOR_GROUPS:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(group), iface))
            sock.setblocking(False)
            return sock
        except Exception:
            sock.close()
            raise

    async def _receive(self, sock: socket.socket, port: int, kind: str) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                data, addr = await loop.sock_recvfrom(sock, 4096)
            except asyncio.CancelledError:
                return
            except OSError:
                return
            if not data:
                continue
            now = time.time()
            self.packets += 1
            self.sources.add(addr[0])
            stat=self.source_stats.setdefault(addr[0],{"packets":0,"ports":set(),"kinds":set(),"first_seen":now,"last_seen":now})
            stat["packets"]+=1;stat["ports"].add(port);stat["kinds"].add(kind);stat["last_seen"]=now
            if kind == "mdns":
                self.inventory.observe(addr[0], data)
            self.ports.add(port)
            if kind == "mdns":
                self.mdns_packets += 1
                lower = data.lower()
                if b"_dante" in lower or b"dante" in lower:
                    self.dante_mdns_packets += 1
                observed_kind = "dante_mdns" if b"dante" in lower else "mdns"
            elif kind == "monitor":
                self.monitor_packets += 1
                observed_kind = "dante_monitor"
            else:
                observed_kind = kind
            self.last = DanteObservation(addr[0], port, observed_kind, len(data), now)

    def snapshot(self) -> dict:
        last = self.last
        now=time.time()
        source_rows=[{"source":ip,"packets":x["packets"],"ports":sorted(x["ports"]),"kinds":sorted(x["kinds"]),"first_seen":x["first_seen"],"last_seen":x["last_seen"],"age_s":round(max(0,now-x["last_seen"]),3),"fresh":(now-x["last_seen"])<20} for ip,x in sorted(self.source_stats.items())]
        return {
            "dante_packets": self.packets,
            "dante_sources": len(self.sources),
            "dante_mdns_packets": self.mdns_packets,
            "dante_mdns_matches": self.dante_mdns_packets,
            "dante_monitor_packets": self.monitor_packets,
            "dante_setup_packets": self.setup_packets,
            "dante_ports": sorted(self.ports),
            "dante_last_source": last.source if last else None,
            "dante_last_kind": last.kind if last else None,
            "dante_last_port": last.port if last else None,
            "dante_last_length": last.length if last else None,
            "dante_last_seen": last.timestamp if last else None,
            "dante_source_stats": source_rows,
            "dante_fresh_sources": sum(1 for x in source_rows if x["fresh"]),
            **self.inventory.snapshot(),
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
