"""Passive SMPTE ST 2110 (RTP video-over-IP) observer.

This never decodes video. It only:

1. Counts RTP packets (RFC 3550 header fields: version, payload type,
   sequence number, timestamp, SSRC) on explicitly configured or
   SAP-discovered multicast video flows.
2. Optionally listens for SAP/SDP session announcements (RFC 2974, the same
   standard mechanism aes67.py already uses for AES67 audio) filtered to
   ``m=video`` media sections, to learn a flow's multicast destination
   without the operator having to type it in by hand. ST 2110-20 raw video
   is announced this way in many real deployments, though large facilities
   more often use NMOS (out of scope here -- a full registration/query API,
   not just a passive listener).

No pixel/frame data is ever parsed or exposed.
"""
from __future__ import annotations

import asyncio
import logging
import re
import socket
import struct
import time
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)

SAP_GROUP = "239.255.255.255"
SAP_PORT = 9875
_RTP_VERSION = 2


@dataclass(frozen=True)
class RTPObservation:
    source: str
    payload_type: int
    sequence: int
    timestamp: int
    ssrc: int
    size: int
    received_at: float = field(default_factory=time.time)


def _parse_rtp_header(data: bytes) -> tuple[int, int, int, int] | None:
    """Return (payload_type, sequence, timestamp, ssrc) or None if not RTP-shaped."""
    if len(data) < 12:
        return None
    first, second = data[0], data[1]
    version = (first >> 6) & 0x03
    if version != _RTP_VERSION:
        return None
    payload_type = second & 0x7F
    sequence, timestamp, ssrc = struct.unpack("!HII", data[2:12])
    return payload_type, sequence, timestamp, ssrc


class ST2110PassiveInspector:
    """Read-only RTP packet counter for one or more ST 2110 video flows."""

    def __init__(self, interface: str = "0.0.0.0", multicast_targets: list[tuple[str, int]] | None = None) -> None:
        self.interface = interface
        self.multicast_targets = list(multicast_targets or [])
        self.packets = 0
        self.rtp_packets = 0
        self.invalid_packets = 0
        self.sources: set[str] = set()
        self.last: RTPObservation | None = None
        self.sdp_sessions: dict[str, dict] = {}
        self._sockets: list[socket.socket] = []
        self._tasks: list[asyncio.Task] = []
        self._sap_sock: socket.socket | None = None
        self._sap_task: asyncio.Task | None = None

    # -- socket setup ------------------------------------------------------------
    def _iface_bytes(self) -> bytes:
        return socket.inet_aton(self.interface if self.interface != "0.0.0.0" else "0.0.0.0")

    def _make_multicast_socket(self, group: str, port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(group), self._iface_bytes()))
        sock.setblocking(False)
        return sock

    async def start(self) -> None:
        if self._tasks or self._sap_task:
            return
        try:
            for group, port in self.multicast_targets:
                sock = self._make_multicast_socket(group, port)
                self._sockets.append(sock)
                self._tasks.append(asyncio.create_task(self._receive_rtp(sock), name=f"show-network-st2110-{port}"))
            self._sap_sock = self._make_multicast_socket(SAP_GROUP, SAP_PORT)
            self._sap_task = asyncio.create_task(self._receive_sap(), name="show-network-st2110-sap")
        except Exception:
            await self.stop()
            raise

    async def add_target(self, group: str, port: int) -> None:
        """Join an additional multicast video flow at runtime (e.g. once discovered via SAP)."""
        if (group, port) in self.multicast_targets:
            return
        sock = self._make_multicast_socket(group, port)
        self.multicast_targets.append((group, port))
        self._sockets.append(sock)
        self._tasks.append(asyncio.create_task(self._receive_rtp(sock), name=f"show-network-st2110-{port}"))

    # -- RTP counting --------------------------------------------------------------
    async def _receive_rtp(self, sock: socket.socket) -> None:
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
            self.packets += 1
            parsed = _parse_rtp_header(data)
            if parsed is None:
                self.invalid_packets += 1
                continue
            payload_type, sequence, timestamp, ssrc = parsed
            self.rtp_packets += 1
            self.sources.add(addr[0])
            self.last = RTPObservation(source=addr[0], payload_type=payload_type, sequence=sequence, timestamp=timestamp, ssrc=ssrc, size=len(data))

    # -- SAP/SDP video flow discovery (mirrors aes67.py, filtered to video) --------
    @staticmethod
    def _extract_sap(data: bytes) -> tuple[bytes, bool] | None:
        if len(data) < 8:
            return None
        first = data[0]
        version = (first >> 5) & 0x07
        addr_type_ipv6 = bool(first & 0x10)
        deletion = bool(first & 0x04)
        encrypted = bool(first & 0x02)
        compressed = bool(first & 0x01)
        auth_words = data[1]
        if version != 1 or addr_type_ipv6 or encrypted or compressed:
            return None
        header_len = 8 + auth_words * 4
        if header_len > len(data):
            return None
        payload = data[header_len:]
        if payload.startswith(b"application/sdp\x00"):
            payload = payload[len(b"application/sdp\x00"):]
        elif payload.startswith(b"v=0"):
            pass
        else:
            nul = payload.find(b"\x00")
            if nul < 0 or payload[:nul].lower() != b"application/sdp":
                return None
            payload = payload[nul + 1:]
        if not payload.lstrip().startswith(b"v=0"):
            return None
        return payload, deletion

    @staticmethod
    def _parse_sdp_video(payload: bytes, source: str, now: float) -> list[tuple[str, dict]]:
        text = payload.decode("utf-8", errors="ignore")
        lines = [x.strip() for x in text.replace("\r", "\n").split("\n") if x.strip()]
        if not lines or lines[0] != "v=0":
            return []
        session: dict[str, list[str]] = {}
        media_sections: list[dict[str, list[str]]] = []
        current = session
        for line in lines:
            if len(line) <= 2 or line[1] != "=":
                continue
            key, value = line[0], line[2:]
            if key == "m":
                current = {"m": [value]}
                media_sections.append(current)
            else:
                current.setdefault(key, []).append(value)
        name = (session.get("s") or [None])[0]
        origin = (session.get("o") or [None])[0]
        session_conn = (session.get("c") or [None])[0]
        rows: list[tuple[str, dict]] = []
        for index, media in enumerate(media_sections):
            mline = (media.get("m") or [""])[0]
            parts = mline.split()
            if len(parts) < 4 or parts[0].lower() != "video":
                continue
            try:
                port = int(parts[1])
            except ValueError:
                continue
            conn = (media.get("c") or [session_conn])[0]
            dest = None
            if conn:
                match = re.search(r"IN IP4 ([0-9.]+)", conn)
                dest = match.group(1) if match else None
            attrs = list(session.get("a", [])) + list(media.get("a", []))
            fmtp = next((a for a in attrs if a.startswith("fmtp:")), None)
            rtpmap = next((a for a in attrs if a.startswith("rtpmap:")), None)
            key = f"{source}|{origin or name or 'session'}|m{index}|{dest or '-'}:{port}"
            rows.append((key, {
                "source": source, "name": name, "origin": origin, "media_index": index,
                "destination": dest, "port": port, "rtpmap": rtpmap, "fmtp": fmtp, "last_seen": now,
            }))
        return rows

    async def _receive_sap(self) -> None:
        loop = asyncio.get_running_loop()
        assert self._sap_sock is not None
        while True:
            try:
                data, addr = await loop.sock_recvfrom(self._sap_sock, 8192)
            except asyncio.CancelledError:
                return
            except OSError:
                return
            if not data:
                continue
            now = time.time()
            parsed = self._extract_sap(data)
            if parsed is None:
                continue
            sdp_payload, deletion = parsed
            rows = self._parse_sdp_video(sdp_payload, addr[0], now)
            if deletion:
                for key, _ in rows:
                    self.sdp_sessions.pop(key, None)
            else:
                for key, row in rows:
                    self.sdp_sessions[key] = row

    # -- reporting -------------------------------------------------------------
    def snapshot(self) -> dict:
        now = time.time()
        last = self.last
        sdp_rows = []
        for row in self.sdp_sessions.values():
            r = dict(row)
            r["age_s"] = round(max(0.0, now - r["last_seen"]), 1)
            r["fresh"] = r["age_s"] < 30.0
            sdp_rows.append(r)
        return {
            "st2110_packets": self.packets,
            "st2110_rtp_packets": self.rtp_packets,
            "st2110_invalid_packets": self.invalid_packets,
            "st2110_sources": len(self.sources),
            "st2110_last_source": last.source if last else None,
            "st2110_last_payload_type": last.payload_type if last else None,
            "st2110_last_sequence": last.sequence if last else None,
            "st2110_last_timestamp": last.timestamp if last else None,
            "st2110_last_size": last.size if last else None,
            "st2110_sdp_sessions": sdp_rows,
            "st2110_sdp_session_count": len(sdp_rows),
            "st2110_targets": [f"{g}:{p}" for g, p in self.multicast_targets],
            "st2110_note": (
                "RTP header counters only; no video is decoded. A flow's "
                "multicast group/port must be explicitly configured (add_target) "
                "or discovered via a real SAP/SDP m=video announcement -- nothing "
                "is guessed."
            ),
        }

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._sap_task:
            self._sap_task.cancel()
        all_tasks = list(self._tasks) + ([self._sap_task] if self._sap_task else [])
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
        self._tasks.clear()
        self._sap_task = None
        for sock in self._sockets:
            try:
                sock.close()
            except OSError:
                pass
        self._sockets.clear()
        if self._sap_sock:
            try:
                self._sap_sock.close()
            except OSError:
                pass
            self._sap_sock = None
