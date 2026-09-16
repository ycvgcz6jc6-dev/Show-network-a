"""Passive PTP observer for Dante/PTPv1, AES67/PTPv2 and related profiles.

Receive-only.  Reported jitter is *packet-arrival timing variation*, not PTP
clock offset.  The observer never participates in BMCA and never adjusts time.
"""
from __future__ import annotations
import logging

from dataclasses import dataclass
import asyncio
import socket
import time

PTP_EVENT_PORT = 319
PTP_GENERAL_PORT = 320
PTP_GROUPS = ("224.0.1.129", "224.0.1.130", "224.0.1.131", "224.0.1.132")


@dataclass(frozen=True)
class PTPObservation:
    source: str
    port: int
    message_type: int | None
    version: int | None
    domain: int | None
    length: int
    timestamp: float
    source_identity: str | None = None


class PTPMonitor:
    def __init__(self, interface: str = "0.0.0.0") -> None:
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.ports: set[int] = set()
        self.groups: set[str] = set()
        self.last = None
        self.event_packets = 0
        self.general_packets = 0
        self._last_time = None
        self.inter_arrival_ms = 0.0
        self.jitter_ms = 0.0
        self._arrival_ewma_ms = None
        self.announce_packets = 0
        self.sync_packets = 0
        self.follow_up_packets = 0
        self.delay_packets = 0
        self.version_counts: dict[int, int] = {}
        self.domain_counts: dict[int, int] = {}
        self.last_source_identity = None
        self.last_grandmaster_identity = None
        self.grandmaster_priority1 = None
        self.grandmaster_clock_class = None
        self.grandmaster_accuracy = None
        self.grandmaster_priority2 = None
        self.grandmaster_last_seen = None
        self._tasks = []
        self._sockets = []
        self.source_stats: dict[str, dict] = {}

    async def start(self):
        if self._tasks:
            return
        try:
            for port in (PTP_EVENT_PORT, PTP_GENERAL_PORT):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
                iface = socket.inet_aton(self.interface if self.interface != "0.0.0.0" else "0.0.0.0")
                for group in PTP_GROUPS:
                    try:
                        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(group) + iface)
                        self.groups.add(group)
                    except OSError:
                        if group == PTP_GROUPS[0]:
                            raise
                sock.setblocking(False)
                self._sockets.append(sock)
                self._tasks.append(asyncio.create_task(self._receive(sock, port), name=f"show-network-ptp-{port}"))
        except Exception:
            await self.stop()
            raise

    @staticmethod
    def _decode_header(data: bytes):
        if len(data) < 2:
            return None, None, None
        version = data[1] & 0x0F
        if version == 2:
            return data[0] & 0x0F, 2, (data[4] if len(data) >= 5 else None)
        if version == 1:
            return None, 1, None
        return None, (version or None), None

    @staticmethod
    def _source_identity(data: bytes, version: int | None) -> str | None:
        if version != 2 or len(data) < 30:
            return None
        clock = data[20:28].hex()
        port = int.from_bytes(data[28:30], "big")
        return f"{clock}:{port}"

    async def _receive(self, sock, port):
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
            msg_type, version, domain = self._decode_header(data)
            source_identity = self._source_identity(data, version)
            if self._last_time is not None:
                inter = max(0.0, (now - self._last_time) * 1000.0)
                if self._arrival_ewma_ms is None:
                    self._arrival_ewma_ms = inter
                    self.jitter_ms = 0.0
                else:
                    # RFC3550-style smoothing concept, but explicitly labelled
                    # packet-arrival variation rather than clock performance.
                    delta = abs(inter - self._arrival_ewma_ms)
                    self.jitter_ms += (delta - self.jitter_ms) / 16.0
                    self._arrival_ewma_ms += (inter - self._arrival_ewma_ms) / 16.0
                self.inter_arrival_ms = inter
            self._last_time = now

            if version is not None:
                self.version_counts[version] = self.version_counts.get(version, 0) + 1
            if domain is not None:
                self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1
            if source_identity:
                self.last_source_identity = source_identity
            if version == 2:
                if msg_type == 0:
                    self.sync_packets += 1
                elif msg_type == 8:
                    self.follow_up_packets += 1
                elif msg_type in (1, 9):
                    self.delay_packets += 1
                elif msg_type == 11:
                    self.announce_packets += 1
                    if len(data) >= 64:
                        self.grandmaster_priority1 = data[47]
                        self.grandmaster_clock_class = data[48]
                        self.grandmaster_accuracy = data[49]
                        self.grandmaster_priority2 = data[52]
                        self.last_grandmaster_identity = data[53:61].hex()
                        self.grandmaster_last_seen = now

            self.packets += 1
            self.event_packets += int(port == PTP_EVENT_PORT)
            self.general_packets += int(port == PTP_GENERAL_PORT)
            self.sources.add(addr[0])
            self.ports.add(port)
            self.last = PTPObservation(addr[0], port, msg_type, version, domain, len(data), now, source_identity)
            stat = self.source_stats.setdefault(addr[0], {
                "packets": 0, "versions": set(), "domains": set(), "ports": set(), "identities": set(), "last_seen": now,
            })
            stat["packets"] += 1
            stat["ports"].add(port)
            stat["last_seen"] = now
            if version is not None:
                stat["versions"].add(version)
            if domain is not None:
                stat["domains"].add(domain)
            if source_identity:
                stat["identities"].add(source_identity)

    def snapshot(self):
        now = time.time()
        last = self.last
        age = (now - self._last_time) if self._last_time else None
        versions = sorted(self.version_counts)
        source_rows = []
        for ip, stats in sorted(self.source_stats.items()):
            src_age = max(0.0, now - stats["last_seen"])
            source_rows.append({
                "source": ip,
                "packets": stats["packets"],
                "versions": sorted(stats["versions"]),
                "domains": sorted(stats["domains"]),
                "ports": sorted(stats["ports"]),
                "source_identities": sorted(stats["identities"]),
                "last_seen": stats["last_seen"],
                "age_s": round(src_age, 3),
                "fresh": src_age < 5.0,
            })
        gm_age = max(0.0, now - self.grandmaster_last_seen) if self.grandmaster_last_seen else None
        return {
            "ptp_packets": self.packets,
            "ptp_sources": len(self.sources),
            "ptp_event_packets": self.event_packets,
            "ptp_general_packets": self.general_packets,
            "ptp_ports": sorted(self.ports),
            "ptp_last_source": last.source if last else None,
            "ptp_last_message_type": last.message_type if last else None,
            "ptp_last_version": last.version if last else None,
            "ptp_versions_observed": versions,
            "ptp_dante_v1_observed": 1 in versions,
            "ptp_v2_observed": 2 in versions,
            "ptp_last_domain": last.domain if last else None,
            "ptp_domains_observed": sorted(self.domain_counts),
            "ptp_last_length": last.length if last else None,
            "ptp_last_seen": last.timestamp if last else None,
            "ptp_inter_arrival_ms": round(self.inter_arrival_ms, 3),
            "ptp_jitter_ms": round(self.jitter_ms, 3),
            "ptp_jitter_semantics": "packet_arrival_variation_not_clock_offset",
            "ptp_clock_offset_ns": None,
            "ptp_clock_offset_available": False,
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
            "ptp_grandmaster_age_s": round(gm_age, 3) if gm_age is not None else None,
            "ptp_clock_present": bool(self.packets and age is not None and age < 5.0),
            "ptp_clock_age_s": round(age, 3) if age is not None else None,
            "ptp_sources_detail": source_rows,
            "ptp_multicast_groups": list(PTP_GROUPS),
            "ptp_interface": self.interface,
            "ptp_measurement_note": "Passive presence/domain/source observation only; no certified PTP offset measurement is inferred.",
        }

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        for sock in self._sockets:
            try:
                sock.close()
            except OSError:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
        self._sockets.clear()
