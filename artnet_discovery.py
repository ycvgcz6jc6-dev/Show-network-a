"""Generic Art-Net node discovery via ArtPoll / ArtPollReply.

Every Art-Net-compliant device (node, controller, media server...) is
required by the Art-Net 4 specification to answer a broadcast ArtPoll
(opcode 0x2000) with an ArtPollReply (opcode 0x2100) carrying its identity:
short/long name, ESTA manufacturer code, MAC address, port count, and a
"Style" byte saying what kind of device it is (node, controller, media
server, router, backup, config tool, visualizer).

This is the standards-based, manufacturer-agnostic way to answer "what
nodes are actually on my network" for ELC/Luminex/ETC/anything else,
without inventing a per-vendor discovery mechanism for each one -- exactly
the same spirit as st2110.py's SAP discovery or topology.py's LLDP walk.

Sending ArtPoll is a broadcast discovery request, not a control action --
the same category of "harmless active probe" this project already accepts
elsewhere (PJLink's own broadcast search in projector_monitor.py). No DMX
or control data is ever sent by this module.
"""
from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Any

_ART_NET_ID = b"Art-Net\x00"
_OP_POLL = 0x2000
_OP_POLL_REPLY = 0x2100
ARTNET_PORT = 6454

STYLE_NAMES = {
    0x00: "Node",
    0x01: "Controller",
    0x02: "Media Server",
    0x03: "Route",
    0x04: "Backup",
    0x05: "Config",
    0x06: "Visualizer",
}

_STALE_AFTER_S = 60.0


def build_art_poll() -> bytes:
    """Build a minimal, spec-compliant ArtPoll packet.

    TalkToMe=0x00 (no diagnostics requested, unicast reply expected via
    node's own reply -- most nodes still broadcast their reply anyway) and
    Priority=0x00 (DpAll, no diagnostic priority filter).
    """
    packet = bytearray()
    packet += _ART_NET_ID
    packet += struct.pack("<H", _OP_POLL)
    packet += struct.pack(">H", 14)  # ProtVer, big-endian per Art-Net spec (14 = Art-Net 4)
    packet.append(0x00)  # TalkToMe
    packet.append(0x00)  # Priority
    return bytes(packet)


def _decode_cstring(raw: bytes) -> str:
    nul = raw.find(b"\x00")
    return raw[: nul if nul >= 0 else len(raw)].decode("utf-8", errors="replace").strip()


def parse_art_poll_reply(data: bytes) -> dict[str, Any] | None:
    """Parse an ArtPollReply. Returns None if ``data`` isn't a valid one
    (silently -- the caller will see plenty of ArtDMX/other traffic too)."""
    if len(data) < 213 or data[:8] != _ART_NET_ID:
        return None
    opcode = struct.unpack("<H", data[8:10])[0]
    if opcode != _OP_POLL_REPLY:
        return None

    ip = ".".join(str(b) for b in data[10:14])
    port = struct.unpack("<H", data[14:16])[0]
    esta_man = struct.unpack("<H", data[24:26])[0]
    short_name = _decode_cstring(data[26:44])
    long_name = _decode_cstring(data[44:108])
    node_report = _decode_cstring(data[108:172])
    num_ports = struct.unpack(">H", data[172:174])[0]
    style_byte = data[200] if len(data) > 200 else 0
    mac = ":".join(f"{b:02x}" for b in data[201:207]) if len(data) >= 207 else None

    return {
        "ip": ip,
        "port": port,
        "esta_manufacturer_code": f"{esta_man:04x}",
        "short_name": short_name,
        "long_name": long_name,
        "node_report": node_report,
        "num_ports": num_ports,
        "style": STYLE_NAMES.get(style_byte, f"unknown(0x{style_byte:02x})"),
        "mac": mac,
    }


async def async_send_poll(interface: str = "0.0.0.0", *, port: int = ARTNET_PORT) -> None:
    """Send one ArtPoll broadcast from ``interface``. Fire-and-forget: the
    replies arrive as ordinary Art-Net packets on the existing receiver
    (see lighting_receiver.py's on_poll_reply callback), not here."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if interface and interface != "0.0.0.0":
            sock.bind((interface, 0))
        sock.sendto(build_art_poll(), ("255.255.255.255", port))
    finally:
        sock.close()


@dataclass
class ArtNetNode:
    ip: str
    short_name: str = ""
    long_name: str = ""
    style: str = ""
    esta_manufacturer_code: str = ""
    manufacturer: str | None = None
    manufacturer_confidence: str | None = None
    num_ports: int = 0
    mac: str | None = None
    node_report: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class ArtNetNodeInventory:
    """Passive registry of Art-Net nodes discovered via ArtPollReply."""

    def __init__(self, stale_after_s: float = _STALE_AFTER_S, match_manufacturer=None) -> None:
        self.nodes: dict[str, ArtNetNode] = {}
        self.stale_after_s = float(stale_after_s)
        # Injected rather than imported directly, so this module has no
        # hard dependency on manufacturer_profiles.py and stays easy to
        # test in isolation; runtime/setup.py wires the real one in.
        self._match_manufacturer = match_manufacturer

    def observe_poll_reply(self, data: bytes, source_ip: str) -> None:
        parsed = parse_art_poll_reply(data)
        if parsed is None:
            return
        ip = parsed["ip"] or source_ip
        now = time.time()
        node = self.nodes.get(ip)
        if node is None:
            node = ArtNetNode(ip=ip, first_seen=now)
            self.nodes[ip] = node
        node.last_seen = now
        node.short_name = parsed["short_name"]
        node.long_name = parsed["long_name"]
        node.style = parsed["style"]
        node.esta_manufacturer_code = parsed["esta_manufacturer_code"]
        node.num_ports = parsed["num_ports"]
        node.mac = parsed["mac"]
        node.node_report = parsed["node_report"]

        if self._match_manufacturer:
            text = f"{node.short_name} {node.long_name}"
            match = self._match_manufacturer(text)
            if match:
                node.manufacturer = match.get("manufacturer")
                node.manufacturer_confidence = match.get("confidence")

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        rows = []
        for node in sorted(self.nodes.values(), key=lambda n: n.ip):
            age = max(0.0, now - node.last_seen)
            rows.append({
                "ip": node.ip,
                "short_name": node.short_name,
                "long_name": node.long_name,
                "style": node.style,
                "manufacturer": node.manufacturer,
                "manufacturer_confidence": node.manufacturer_confidence,
                "esta_manufacturer_code": node.esta_manufacturer_code,
                "num_ports": node.num_ports,
                "mac": node.mac,
                "node_report": node.node_report,
                "age_s": round(age, 1),
                "fresh": age < self.stale_after_s,
            })
        return {
            "artnet_nodes": rows,
            "artnet_node_count": len(rows),
            "artnet_nodes_by_style": {
                style: sum(1 for r in rows if r["style"] == style)
                for style in sorted({r["style"] for r in rows})
            },
            "artnet_note": (
                "Discovered via standard ArtPoll/ArtPollReply (Art-Net 4 spec), "
                "manufacturer-agnostic. Manufacturer field is a best-effort text "
                "match against short/long name, not guaranteed."
            ),
        }
