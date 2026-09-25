"""Passive AES67 SAP/SDP discovery observer.

SAP framing is validated before SDP is accepted.  Each SDP media section is
kept separate so multi-stream announcements cannot mix port/codec metadata.
"""
from __future__ import annotations

import asyncio
import re
import socket
import struct
import time
from dataclasses import dataclass

SAP_GROUP = "239.255.255.255"
SAP_PORT = 9875


@dataclass(frozen=True)
class SAPObservation:
    source: str
    length: int
    timestamp: float
    payload_hint: str


class AES67Monitor:
    def __init__(self, interface="0.0.0.0"):
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.last = None
        self.sessions: dict[str, dict] = {}
        self.invalid_packets = 0
        self.deleted_sessions = 0
        self._sock = None
        self._task = None

    async def start(self):
        if self._task:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", SAP_PORT))
            iface = socket.inet_aton(self.interface if self.interface != "0.0.0.0" else "0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(SAP_GROUP), iface))
            sock.setblocking(False)
            self._sock = sock
            self._task = asyncio.create_task(self._receive(), name="show-network-aes67")
        except Exception:
            sock.close()
            self._sock = None
            self._task = None
            raise

    @staticmethod
    def _extract_sap(data: bytes) -> tuple[bytes, bool] | None:
        """Return (SDP payload, deletion flag) for an unencrypted IPv4 SAP packet."""
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
        # RFC 2974 payload type is a zero-terminated MIME string; legacy SAP
        # senders may omit it. Accept only SDP after the validated SAP header.
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
    def _parse_sdp_payload(payload: bytes, source: str, now: float) -> list[tuple[str, dict]]:
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
        session_attrs = list(session.get("a", []))
        rows: list[tuple[str, dict]] = []

        for index, media in enumerate(media_sections):
            mline = (media.get("m") or [""])[0]
            parts = mline.split()
            if len(parts) < 4 or parts[0].lower() != "audio":
                continue
            try:
                port = int(parts[1])
            except ValueError:
                continue
            payload_types = parts[3:]
            conn = (media.get("c") or [session_conn])[0]
            dest = None
            if conn:
                match = re.search(r"IN IP4 ([0-9.]+)", conn)
                dest = match.group(1) if match else None
            attrs = session_attrs + list(media.get("a", []))
            rtpmap_by_pt: dict[str, str] = {}
            ptime = None
            clocks: list[str] = []
            sync_time = None
            for attr in attrs:
                if attr.startswith("rtpmap:"):
                    left, sep, codec = attr.partition(" ")
                    if sep:
                        rtpmap_by_pt[left.split(":", 1)[1]] = codec
                elif attr.startswith("ptime:"):
                    ptime = attr.split(":", 1)[1]
                elif attr.startswith("ts-refclk:") or attr.startswith("mediaclk:"):
                    clocks.append(attr)
                elif attr.startswith("sync-time:"):
                    sync_time = attr.split(":", 1)[1]

            for payload_type in payload_types:
                codec = rtpmap_by_pt.get(payload_type)
                encoding = sample_rate = channels = None
                if codec:
                    bits = codec.split("/")
                    encoding = bits[0] if bits else None
                    try:
                        sample_rate = int(bits[1]) if len(bits) > 1 else None
                    except ValueError:
                        sample_rate = None
                    try:
                        channels = int(bits[2]) if len(bits) > 2 else 1
                    except ValueError:
                        channels = None
                key = f"{source}|{origin or name or 'session'}|m{index}|{dest or '-'}:{port}|pt{payload_type}"
                rows.append((key, {
                    "source": source,
                    "name": name,
                    "origin": origin,
                    "media_index": index,
                    "destination": dest,
                    "port": port,
                    "payload_type": payload_type,
                    "rtpmap": f"rtpmap:{payload_type} {codec}" if codec else None,
                    "encoding": encoding,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "ptime_ms": ptime,
                    "clock": " | ".join(clocks) if clocks else None,
                    "sync_time": sync_time,
                    "last_seen": now,
                }))
        return rows

    @classmethod
    def _parse_sdp(cls, data: bytes, source: str, now: float):
        """Compatibility helper used by older tests: returns first media row."""
        sap = cls._extract_sap(data)
        payload = sap[0] if sap else (data[data.find(b"v=0"):] if b"v=0" in data else b"")
        rows = cls._parse_sdp_payload(payload, source, now)
        return rows[0] if rows else None

    async def _receive(self):
        loop = asyncio.get_running_loop()
        assert self._sock is not None
        while True:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 8192)
            except asyncio.CancelledError:
                return
            except OSError:
                return
            if not data:
                continue
            now = time.time()
            parsed_sap = self._extract_sap(data)
            if parsed_sap is None:
                self.invalid_packets += 1
                self.last = SAPObservation(addr[0], len(data), now, "invalid_sap")
                continue
            payload, deletion = parsed_sap
            rows = self._parse_sdp_payload(payload, addr[0], now)
            if not rows:
                self.invalid_packets += 1
                self.last = SAPObservation(addr[0], len(data), now, "sap_without_valid_audio_sdp")
                continue
            self.packets += 1
            self.sources.add(addr[0])
            if deletion:
                for key, _ in rows:
                    if self.sessions.pop(key, None) is not None:
                        self.deleted_sessions += 1
                hint = "sdp_delete"
            else:
                for key, row in rows:
                    self.sessions[key] = row
                hint = "sdp"
            self.last = SAPObservation(addr[0], len(data), now, hint)

    def snapshot(self):
        now = time.time()
        rows = []
        for row in self.sessions.values():
            r = dict(row)
            r["age_s"] = round(max(0.0, now - r["last_seen"]), 3)
            r["fresh"] = r["age_s"] < 30.0
            rows.append(r)
        rows.sort(key=lambda r: (r.get("name") or "", r.get("media_index", 0), r.get("payload_type") or ""))
        return {
            "aes67_sap_packets": self.packets,
            "aes67_sap_invalid_packets": self.invalid_packets,
            "aes67_sap_deleted_sessions": self.deleted_sessions,
            "aes67_sap_sources": len(self.sources),
            "aes67_last_source": self.last.source if self.last else None,
            "aes67_last_length": self.last.length if self.last else None,
            "aes67_last_hint": self.last.payload_hint if self.last else None,
            "aes67_last_seen": self.last.timestamp if self.last else None,
            "aes67_sessions": rows,
            "aes67_session_count": len(rows),
            "aes67_fresh_sessions": sum(1 for r in rows if r["fresh"]),
            "aes67_sap_group": SAP_GROUP,
            "aes67_sap_port": SAP_PORT,
            "aes67_parser_note": "Validated SAP + per-media SDP parsing; zero sessions means no valid announcement observed.",
        }

    async def stop(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        if self._sock:
            self._sock.close()
        self._sock = None
