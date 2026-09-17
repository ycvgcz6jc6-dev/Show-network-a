"""Tests for custom_components/dmx_monitor/artnet_discovery.py."""
from __future__ import annotations

import socket
import struct

from custom_components.dmx_monitor.artnet_discovery import (
    ArtNetNodeInventory,
    build_art_poll,
    parse_art_poll_reply,
)


def _build_fake_reply(ip, short_name, long_name, mac_bytes, style=0x00, num_ports=4):
    pkt = bytearray(239)
    pkt[0:8] = b"Art-Net\x00"
    pkt[8:10] = struct.pack("<H", 0x2100)
    pkt[10:14] = socket.inet_aton(ip)
    pkt[14:16] = struct.pack("<H", 6454)
    sb = short_name.encode()[:17]
    pkt[26:26 + len(sb)] = sb
    lb = long_name.encode()[:63]
    pkt[44:44 + len(lb)] = lb
    pkt[172:174] = struct.pack(">H", num_ports)
    pkt[200] = style
    pkt[201:207] = mac_bytes
    return bytes(pkt)


def test_build_art_poll_is_well_formed():
    poll = build_art_poll()
    assert poll[:8] == b"Art-Net\x00"
    assert struct.unpack("<H", poll[8:10])[0] == 0x2000


def test_parse_art_poll_reply_extracts_identity():
    reply = _build_fake_reply("10.2.1.50", "LumiNode12", "Luminex LumiNode 12", bytes.fromhex("001122334455"), num_ports=12)
    parsed = parse_art_poll_reply(reply)
    assert parsed["ip"] == "10.2.1.50"
    assert parsed["short_name"] == "LumiNode12"
    assert parsed["long_name"] == "Luminex LumiNode 12"
    assert parsed["style"] == "Node"
    assert parsed["num_ports"] == 12
    assert parsed["mac"] == "00:11:22:33:44:55"


def test_parse_art_poll_reply_rejects_garbage_and_wrong_opcode():
    assert parse_art_poll_reply(b"garbage") is None
    assert parse_art_poll_reply(build_art_poll()) is None  # a real ArtPoll, wrong opcode for a reply


def test_inventory_identifies_multiple_manufacturers_from_real_replies():
    def fake_match_manufacturer(text):
        text = text.lower()
        if "luminex" in text:
            return {"manufacturer": "Luminex", "confidence": "candidate"}
        if "elc" in text:
            return {"manufacturer": "ELC Lighting", "confidence": "candidate"}
        return None

    inventory = ArtNetNodeInventory(match_manufacturer=fake_match_manufacturer)
    inventory.observe_poll_reply(
        _build_fake_reply("10.2.1.50", "LumiNode12", "Luminex LumiNode 12", bytes.fromhex("001122334455")),
        "10.2.1.50",
    )
    inventory.observe_poll_reply(
        _build_fake_reply("10.2.1.51", "dmXLAN", "ELC Lighting dmXLAN Node", bytes.fromhex("001122334456")),
        "10.2.1.51",
    )

    snapshot = inventory.snapshot()
    assert snapshot["artnet_node_count"] == 2
    by_ip = {row["ip"]: row for row in snapshot["artnet_nodes"]}
    assert by_ip["10.2.1.50"]["manufacturer"] == "Luminex"
    assert by_ip["10.2.1.51"]["manufacturer"] == "ELC Lighting"


def test_inventory_distinguishes_console_from_node_by_style():
    inventory = ArtNetNodeInventory()
    inventory.observe_poll_reply(_build_fake_reply("10.2.1.20", "Node", "A Node", bytes.fromhex("001122334455"), style=0x00), "10.2.1.20")
    inventory.observe_poll_reply(_build_fake_reply("10.2.1.1", "MA3", "grandMA3 full-size", bytes.fromhex("001122334458"), style=0x01), "10.2.1.1")

    snapshot = inventory.snapshot()
    by_ip = {row["ip"]: row for row in snapshot["artnet_nodes"]}
    assert by_ip["10.2.1.20"]["style"] == "Node"
    assert by_ip["10.2.1.1"]["style"] == "Controller"
    assert snapshot["artnet_nodes_by_style"] == {"Controller": 1, "Node": 1}
