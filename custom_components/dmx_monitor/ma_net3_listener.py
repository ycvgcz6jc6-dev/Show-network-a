"""Passive MA-Net3 multicast listener.

Receive-only: the integration never sends MA-Net3/session/control payloads.
The listener maps traffic to an MA session index from the multicast group that
carried it.  It does not join an MA session and it never sends MA commands.
"""
from __future__ import annotations
import asyncio
import socket
from dataclasses import dataclass
from time import monotonic, time

MA_NET3_PORT = 30020
MA_BASES = ("236.4.1", "239.4.1")
SESSION_COUNT = 32


def session_groups(index: int, base: str) -> tuple[str, ...]:
    """Return the four MA-Net3 multicast groups for session index 0..31.

    MA documents BaseIP+4*X and gives session index 3 as .13-.16; using
    X directly therefore maps index 0 to .1-.4 and index 31 to .125-.128.
    """
    if not 0 <= int(index) < SESSION_COUNT:
        raise ValueError("session index must be 0..31")
    start = 1 + 4 * int(index)
    return tuple(f"{base}.{start + offset}" for offset in range(4))


@dataclass(frozen=True)
class MAObservation:
    source_ip: str
    destination_group: str
    size: int
    received_at: float
    session_index: int | None = None
    multicast_base: str | None = None


class MANet3Listener:
    def __init__(self, interface_ip: str, groups=None, port=MA_NET3_PORT):
        self.interface_ip = interface_ip
        self.port = port
        self.transports = []
        self.observations: list[MAObservation] = []
        self.packet_count = 0
        self.last_seen: float | None = None
        self.bytes = 0
        self.sources: set[str] = set()
        self.groups_seen: set[str] = set()
        self.session_indexes_seen: set[int] = set()
        self.state = "starting"
        self.last_error: str | None = None
        self.bound_endpoint: str | None = None
        self.joined_groups: list[str] = []
        self.join_errors: list[str] = []
        self.last_source: str | None = None
        self.last_packet_epoch: float | None = None
        self.last_packet_size: int | None = None
        self.last_packet_prefix_hex: str | None = None
        self.last_packet_prefix_ascii: str | None = None
        self.source_stats: dict[str, dict] = {}
        self.session_stats: dict[int, dict] = {}
        self._precise_group_routing = True
        self._legacy_groups = tuple(groups or ())

    def _make_socket(self, groups: tuple[str, ...]) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.port))
        # Linux normally delivers multicast joined by another socket to all
        # sockets bound to the port. Disabling IP_MULTICAST_ALL makes the
        # per-session socket a trustworthy session-index observer.
        try:
            opt = getattr(socket, "IP_MULTICAST_ALL", 49)
            sock.setsockopt(socket.IPPROTO_IP, opt, 0)
        except OSError:
            self._precise_group_routing = False
        for group in groups:
            membership = socket.inet_aton(group) + socket.inet_aton(self.interface_ip)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            self.joined_groups.append(group)
        sock.setblocking(False)
        return sock

    async def start(self):
        if self.transports:
            return
        loop = asyncio.get_running_loop()
        self.joined_groups = []
        self.join_errors = []
        try:
            # Administration groups are not session evidence by themselves.
            admin_groups = tuple(f"{base}.0" for base in MA_BASES)
            sock = self._make_socket(admin_groups)
            self.bound_endpoint = f"{sock.getsockname()[0]}:{sock.getsockname()[1]}"
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _Protocol(self, "admin", None, None), sock=sock
            )
            self.transports.append(transport)

            # One socket per session index, joining both the default and
            # alternate multicast bases. This avoids 128 sockets while still
            # providing passive session-index evidence.
            for idx in range(SESSION_COUNT):
                groups = tuple(g for base in MA_BASES for g in session_groups(idx, base))
                try:
                    sock = self._make_socket(groups)
                    transport, _ = await loop.create_datagram_endpoint(
                        lambda idx=idx: _Protocol(self, f"session:{idx}", idx, None), sock=sock
                    )
                    self.transports.append(transport)
                except OSError as err:
                    self.join_errors.append(f"session {idx}: {type(err).__name__}: {err}")
                    raise
            self.state = "listening"
            self.last_error = None
        except Exception as err:
            self.state = "error"
            self.last_error = f"{type(err).__name__}: {err}"
            await self.stop()
            raise

    async def stop(self):
        for transport in self.transports:
            transport.close()
        self.transports.clear()

    def record(self, data: bytes, addr, group: str, session_index: int | None = None, multicast_base: str | None = None):
        now = monotonic()
        source = addr[0]
        self.packet_count += 1
        self.bytes += len(data)
        self.last_seen = now
        self.last_packet_epoch = time()
        self.last_source = source
        self.last_packet_size = len(data)
        prefix = bytes(data[:24])
        self.last_packet_prefix_hex = prefix.hex(" ")
        self.last_packet_prefix_ascii = "".join(chr(b) if 32 <= b < 127 else "." for b in prefix)
        stats = self.source_stats.setdefault(source, {"packets": 0, "bytes": 0, "last_packet_epoch": None, "last_size": 0, "prefix_hex": "", "prefix_ascii": "", "session_indexes": set()})
        stats["packets"] += 1
        stats["bytes"] += len(data)
        stats["last_packet_epoch"] = self.last_packet_epoch
        stats["last_size"] = len(data)
        stats["prefix_hex"] = self.last_packet_prefix_hex
        stats["prefix_ascii"] = self.last_packet_prefix_ascii
        if session_index is not None and self._precise_group_routing:
            stats["session_indexes"].add(session_index)
            self.session_indexes_seen.add(session_index)
            ss = self.session_stats.setdefault(session_index, {"packets": 0, "bytes": 0, "sources": set(), "last_packet_epoch": None})
            ss["packets"] += 1; ss["bytes"] += len(data); ss["sources"].add(source); ss["last_packet_epoch"] = self.last_packet_epoch
        else:
            session_index = None
        self.sources.add(source)
        self.groups_seen.add(group)
        self.observations.append(MAObservation(source, group, len(data), now, session_index, multicast_base))
        if len(self.observations) > 500:
            del self.observations[:-500]

    def snapshot(self) -> dict:
        raw_sources=[]
        for ip, stats in sorted(self.source_stats.items()):
            row={k:v for k,v in stats.items() if k != "session_indexes"}
            row["session_indexes"] = sorted(stats.get("session_indexes", set()))
            raw_sources.append({"source_ip": ip, **row})
        sessions=[]
        for idx, stats in sorted(self.session_stats.items()):
            sessions.append({"session_index": idx, "packets": stats["packets"], "bytes": stats["bytes"], "sources": sorted(stats["sources"]), "source_count": len(stats["sources"]), "last_packet_epoch": stats["last_packet_epoch"]})
        return {
            "packets": self.packet_count,
            "bytes": self.bytes,
            "sources": len(self.sources),
            "groups": len(self.groups_seen),
            "last_seen": self.last_seen,
            "observations": list(self.observations[-100:]),
            "sessions": sessions,
            "diagnostics": {
                "state": self.state, "interface": self.interface_ip, "port": self.port,
                "bound_endpoint": self.bound_endpoint, "configured_groups": len(self.joined_groups),
                "joined_groups": list(self.joined_groups), "joined_group_count": len(self.joined_groups),
                "join_errors": list(self.join_errors), "last_error": self.last_error,
                "last_source": self.last_source, "last_packet_epoch": self.last_packet_epoch,
                "last_packet_size": self.last_packet_size,
                "last_packet_prefix_hex": self.last_packet_prefix_hex,
                "last_packet_prefix_ascii": self.last_packet_prefix_ascii,
                "raw_sources": raw_sources,
                "session_indexes_seen": sorted(self.session_indexes_seen),
                "session_group_mapping": self._precise_group_routing,
                "multicast_bases": [f"{b}.x" for b in MA_BASES],
                "receive_only": True,
            },
        }


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, owner: MANet3Listener, group: str, session_index: int | None, multicast_base: str | None):
        self.owner = owner
        self.group = group
        self.session_index = session_index
        self.multicast_base = multicast_base
    def datagram_received(self, data, addr):
        self.owner.record(data, addr, self.group, self.session_index, self.multicast_base)
