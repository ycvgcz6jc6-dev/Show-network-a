"""Passive Green-GO Digital Intercom network observer.

Read-only. This module never sends Green-GO device/application traffic
and never joins a Talk/Call/Cue session -- it only counts packets
arriving on the configured multicast group and port, to answer "is
something transmitting there" for GreenGOInventory.observe().

WHY THE MULTICAST GROUP IS A REQUIRED SETTING, NOT AUTO-DISCOVERED:
Verified directly against Green-GO's own official documentation
(manual.greengoconnect.com/en/guides/network,
manual.greengoconnect.com/en/glossary): device-device and device-
application communication both happen over UDP port 5810 on a
*multicast* group, but unlike Dante (fixed, Audinate-assigned multicast
ranges) or PTP (fixed IEEE 1588 multicast addresses), Green-GO's
multicast address is "generated at the creation time of the
configuration file based on the configuration ID" -- i.e. it is
per-installation, not a protocol-fixed value this integration could
hardcode or guess. No separate, address-independent discovery/broadcast
channel is documented either. So unlike audio_ptp.py/dante.py, which
join well-known fixed groups unconditionally, this module can only
listen once told which group to join -- the same multicast address the
installation's own Green-GO configuration file already uses.

WHY THIS DOES NOT DECODE MESSAGE CONTENT (Talk/Call/Cue/Listen/levels):
The original research notes for this project studied one publicly
available Green-GO control script and observed message forms like
"MIXER:..."-style OSC-ish addresses, but explicitly cautioned that a
single studied script is not proof of the full, general wire format
(number of channels, exact addresses, heartbeat period all called out
as unconfirmed there). Without a verified, general specification for
the UDP 5810 payload, this module only detects *presence* (a source is
sending packets on the configured group/port) and never parses payload
content -- the same "observe, don't decode the undocumented parts"
boundary applied to Dante's own monitoring traffic in dante.py.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import socket
import struct
import time

GREENGO_PORT = 5810


@dataclass(frozen=True)
class GreenGOObservation:
    source: str
    length: int
    timestamp: float


class GreenGOMonitor:
    """Passively counts UDP 5810 multicast packets on one user-specified
    Green-GO configuration's multicast group. Never transmits."""

    def __init__(self, multicast_group: str, interface: str = "0.0.0.0") -> None:
        self.multicast_group = multicast_group
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.source_stats: dict[str, dict] = {}
        self.last: GreenGOObservation | None = None
        self._task: asyncio.Task | None = None
        self._socket: socket.socket | None = None

    async def start(self) -> None:
        if self._task:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", GREENGO_PORT))
            iface = socket.inet_aton(self.interface) if self.interface != "0.0.0.0" else socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(self.multicast_group), iface))
            sock.setblocking(False)
            self._socket = sock
            self._task = asyncio.create_task(self._receive(sock), name="show-network-greengo")
        except Exception:
            await self.stop()
            raise

    async def _receive(self, sock: socket.socket) -> None:
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
            stat = self.source_stats.setdefault(addr[0], {"packets": 0, "first_seen": now, "last_seen": now})
            stat["packets"] += 1
            stat["last_seen"] = now
            self.last = GreenGOObservation(addr[0], len(data), now)

    def snapshot(self) -> dict:
        now = time.time()
        source_rows = [
            {"source": ip, "packets": stat["packets"], "first_seen": stat["first_seen"],
             "last_seen": stat["last_seen"], "age_s": round(max(0.0, now - stat["last_seen"]), 3),
             "fresh": (now - stat["last_seen"]) < 10.0}
            for ip, stat in sorted(self.source_stats.items())
        ]
        return {
            "greengo_packets": self.packets,
            "greengo_sources": len(self.sources),
            "greengo_source_stats": source_rows,
            "greengo_fresh_sources": sum(1 for r in source_rows if r["fresh"]),
            "greengo_multicast_group": self.multicast_group,
            "greengo_last_seen": self.last.timestamp if self.last else None,
            "greengo_scope": "presence_only_no_payload_decoded",
        }

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
