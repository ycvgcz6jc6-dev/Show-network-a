"""Real, byte-accurate sACN (ANSI E1.31) and Art-Net packet builders for
tests. Field offsets verified against the real protocol spec and
cross-checked by round-tripping through the real parse_sacn_dmp/
parse_artnet_dmx before being used as test fixtures (see
test_lighting_receiver.py).
"""
import struct


def build_sacn_packet(universe=1, priority=100, sequence=1, values=None,
                       source_name="Test Console", cid=b"\x01" * 16):
    values = values or [0] * 512
    dmx_data = bytes([0x00] + list(values))  # DMX start code + up to 512 channels
    property_count = len(dmx_data)

    packet = bytearray(126 + 512)
    packet[0:2] = struct.pack(">H", 0x0010)  # preamble size
    packet[2:4] = struct.pack(">H", 0x0000)  # postamble size
    packet[4:16] = b"ASC-E1.17\x00\x00\x00"  # ACN packet identifier
    packet[22:38] = cid
    name_bytes = source_name.encode("utf-8")[:63]
    packet[44:44 + len(name_bytes)] = name_bytes
    packet[108] = priority
    packet[111] = sequence & 0xFF
    packet[113:115] = struct.pack(">H", universe)
    packet[123:125] = struct.pack(">H", property_count)
    packet[126:126 + len(dmx_data) - 1] = bytes(dmx_data[1:])
    return bytes(packet)


def build_artnet_packet(universe=0, values=None):
    values = values or [0] * 512
    packet = bytearray()
    packet += b"Art-Net\x00"
    packet += struct.pack("<H", 0x5000)  # OpDmx
    packet += struct.pack(">H", 14)      # protocol version
    packet += bytes([0, 0])              # sequence, physical
    packet += struct.pack("<H", universe)
    packet += struct.pack(">H", len(values))
    packet += bytes(values)
    return bytes(packet)
