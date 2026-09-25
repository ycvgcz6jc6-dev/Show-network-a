"""Tests for lighting_receiver.py -- the core sACN/Art-Net receiver. No
test previously existed for this module despite it being the literal
heart of "DMX Monitor". Packet fixtures in _dmx_packet_builders.py are
real, byte-accurate ANSI E1.31 (sACN) and Art-Net packets, verified by
round-tripping through the real parser before being used here.

One real bug found and fixed while writing these tests: a brand new
source's *second*-ever packet reported "jitter" equal to its entire
inter-arrival interval (e.g. a perfectly regular 25ms source showed
25ms of false jitter right as it started), because there was no real
previous interval yet to diff against. See the jitter-related tests
below and lighting_receiver.py's own inline comment for the fix.
"""
from __future__ import annotations

import pytest

import custom_components.dmx_monitor.lighting_receiver as lr
from custom_components.dmx_monitor.lighting_receiver import (
    UniverseTracker, parse_sacn_dmp, parse_artnet_dmx,
)
from tests._dmx_packet_builders import build_sacn_packet, build_artnet_packet


# --- parse_sacn_dmp / parse_artnet_dmx: real wire format -------------------

def test_parse_sacn_dmp_real_packet_all_fields():
    packet = build_sacn_packet(universe=5, priority=150, sequence=42,
                                values=[255] * 512, source_name="FOH Console")
    universe, priority, sequence, values, cid, source_name = parse_sacn_dmp(packet)
    assert universe == 5
    assert priority == 150
    assert sequence == 42
    assert len(values) == 512
    assert values == bytes([255] * 512)
    assert source_name == "FOH Console"
    assert len(cid) == 32  # 16 bytes hex-encoded


def test_parse_sacn_dmp_rejects_too_short():
    assert parse_sacn_dmp(b"\x00\x10short") is None


def test_parse_sacn_dmp_rejects_wrong_preamble():
    packet = bytearray(build_sacn_packet())
    packet[0:2] = b"\xff\xff"
    assert parse_sacn_dmp(bytes(packet)) is None


def test_parse_sacn_dmp_rejects_missing_acn_identifier():
    packet = bytearray(build_sacn_packet())
    packet[4:16] = b"NOTACN\x00\x00\x00\x00\x00\x00"
    assert parse_sacn_dmp(bytes(packet)) is None


def test_parse_artnet_dmx_real_packet():
    packet = build_artnet_packet(universe=3, values=[200] * 512)
    universe, values = parse_artnet_dmx(packet)
    assert universe == 3
    assert len(values) == 512
    assert values[0] == 200


def test_parse_artnet_dmx_rejects_wrong_signature():
    packet = bytearray(build_artnet_packet())
    packet[0:8] = b"NotArtN\x00"
    assert parse_artnet_dmx(bytes(packet)) is None


def test_parse_artnet_dmx_rejects_wrong_opcode():
    packet = bytearray(build_artnet_packet())
    packet[8:10] = b"\x00\x00"  # not OpDmx
    assert parse_artnet_dmx(bytes(packet)) is None


def test_parse_artnet_dmx_rejects_too_short():
    assert parse_artnet_dmx(b"Art-Net\x00short") is None


# --- UniverseTracker: jitter regression -------------------------------------

@pytest.fixture
def controlled_clock(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(lr, "monotonic", lambda: t[0])
    return t


def test_first_packet_has_zero_jitter_and_zero_inter_arrival(controlled_clock):
    tracker = UniverseTracker()
    item = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=1)
    assert item.inter_arrival_ms == 0.0
    assert item.jitter_ms == 0.0


def test_second_packet_of_regular_source_has_zero_jitter_not_full_interval(controlled_clock):
    """Regression test for the false-jitter-spike bug: a perfectly
    regular 25ms source must show 0 jitter on its second packet, not
    25ms (the whole interval, from diffing against a placeholder)."""
    tracker = UniverseTracker()
    t = controlled_clock
    tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=1)
    t[0] += 0.025
    item2 = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=2)
    assert item2.inter_arrival_ms == 25.0
    assert item2.jitter_ms == 0.0


def test_perfectly_regular_source_shows_zero_jitter_throughout(controlled_clock):
    tracker = UniverseTracker()
    t = controlled_clock
    jitters = []
    for seq in range(1, 6):
        item = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=seq)
        jitters.append(item.jitter_ms)
        t[0] += 0.025
    assert jitters == [0.0, 0.0, 0.0, 0.0, 0.0]


def test_real_timing_variation_is_still_detected_from_third_packet_on(controlled_clock):
    """The fix must not suppress genuine jitter -- only the false
    second-packet spike."""
    tracker = UniverseTracker()
    t = controlled_clock
    deltas = [0.025, 0.025, 0.030, 0.020]  # regular, regular, late, early
    items = []
    for i, d in enumerate(deltas):
        items.append(tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=i + 1))
        t[0] += d
    # items[0]=seq1 (t=1000.000), items[1]=seq2 (t=1000.025, inter=25),
    # items[2]=seq3 (t=1000.050, inter=25, jitter=0), items[3]=seq4 (t=1000.080, inter=30, jitter=5)
    assert items[2].jitter_ms == 0.0
    assert items[3].inter_arrival_ms == 30.0
    assert items[3].jitter_ms == 5.0


def test_jitter_state_does_not_leak_between_different_sources(controlled_clock):
    """Each (protocol, universe, source) key must track its own interval
    history independently."""
    tracker = UniverseTracker()
    t = controlled_clock
    tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=1)
    t[0] += 0.025
    tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=2)  # source A, 2nd packet
    item_b1 = tracker.observe("sACN", 1, "10.1.1.2", bytes(512), sequence=1)  # source B, 1st packet
    assert item_b1.jitter_ms == 0.0
    assert item_b1.inter_arrival_ms == 0.0


# --- UniverseTracker: sequence loss (sACN only, 8-bit wraparound) ----------

def test_sequence_loss_zero_for_consecutive_packets(controlled_clock):
    tracker = UniverseTracker()
    t = controlled_clock
    last = None
    for seq in range(1, 6):
        last = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=seq)
        t[0] += 0.025
    assert last.sequence_loss_pct == 0.0


def test_sequence_loss_detects_a_real_gap(controlled_clock):
    tracker = UniverseTracker()
    t = controlled_clock
    tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=1)
    t[0] += 0.025
    # Jump from 1 to 5: sequences 2, 3, 4 are missing (3 lost packets).
    item = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=5)
    assert item.sequence_loss_pct > 0.0


def test_sequence_number_rollover_255_to_0_is_not_counted_as_loss(controlled_clock):
    tracker = UniverseTracker()
    t = controlled_clock
    last = None
    for seq in (254, 255, 0, 1):
        last = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=seq)
        t[0] += 0.025
    assert last.sequence_loss_pct == 0.0


def test_sequence_loss_not_tracked_for_artnet():
    """Art-Net has no sequence-loss-relevant field parsed here (sequence
    is always None for Art-Net in the receiver's own on_frame call) --
    loss tracking is sACN-specific."""
    tracker = UniverseTracker()
    item = tracker.observe("Art-Net", 1, "10.1.1.1", bytes(512), sequence=None)
    assert item.sequence_loss_pct == 0.0


# --- UniverseTracker: last_change tracking ---------------------------------

def test_last_change_is_none_on_first_observation(controlled_clock):
    tracker = UniverseTracker()
    item = tracker.observe("sACN", 1, "10.1.1.1", bytes(512), sequence=1)
    assert item.last_change is None


def test_last_change_updates_only_when_values_actually_differ(controlled_clock):
    tracker = UniverseTracker()
    t = controlled_clock
    vals_a = bytes([10] * 512)
    vals_b = bytes([20] * 512)
    tracker.observe("sACN", 1, "10.1.1.1", vals_a, sequence=1)
    t[0] += 0.025
    same = tracker.observe("sACN", 1, "10.1.1.1", vals_a, sequence=2)  # identical values
    assert same.last_change is None
    t[0] += 0.025
    changed = tracker.observe("sACN", 1, "10.1.1.1", vals_b, sequence=3)  # different values
    assert changed.last_change == t[0]


# --- UniverseTracker: bounded eviction --------------------------------------

def test_tracker_evicts_oldest_key_once_over_max_items(controlled_clock):
    tracker = UniverseTracker(max_items=64)
    t = controlled_clock
    for i in range(70):
        tracker.observe("sACN", 1, f"10.1.1.{i}", bytes(512), sequence=1)
        t[0] += 0.001
    assert len(tracker.all()) <= 64


def test_tracker_eviction_removes_earliest_source_first():
    tracker = UniverseTracker(max_items=64)
    for i in range(70):
        tracker.observe("sACN", 1, f"10.1.1.{i}", bytes(512), sequence=1)
    sources = {item.source for item in tracker.all()}
    assert "10.1.1.0" not in sources  # the very first source, evicted first
    assert "10.1.1.69" in sources     # the most recent source, still present


# --- active_channels counting -----------------------------------------------

def test_active_channels_counts_only_nonzero_bytes(controlled_clock):
    tracker = UniverseTracker()
    values = bytes([0] * 500 + [1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0])
    item = tracker.observe("sACN", 1, "10.1.1.1", values, sequence=1)
    assert item.active_channels == 5
