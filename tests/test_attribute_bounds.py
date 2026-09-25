"""Tests for custom_components/dmx_monitor/attribute_bounds.py.

Covers the P1 audit fix: entity attributes must never exceed Home
Assistant Recorder's 16384-byte limit, validated with the audit's own
stated acceptance criterion (500 simulated devices).
"""
from __future__ import annotations

import json

from custom_components.dmx_monitor.attribute_bounds import bound_attributes


def test_small_payload_passes_through_untouched():
    small = {"devices": [{"name": "Device 1"}, {"name": "Device 2"}]}
    assert bound_attributes(small) == small


def test_large_payload_stays_under_recorder_limit_with_500_devices():
    devices = [
        {
            "unique_id": f"candidate:10.0.{i // 254}.{i % 254}",
            "display_name": f"Device {i} Console Full-Size Edition Extended Name",
            "display_manufacturer": "MA Lighting International GmbH",
            "display_model": "grandMA3 full-size",
            "protocols": ["sACN", "Art-Net", "MA-Net3"],
            "confidence": 0.95,
        }
        for i in range(500)
    ]
    raw = {"devices": devices}
    raw_size = len(json.dumps(raw, default=str).encode("utf-8"))
    assert raw_size > 16384  # sanity check: the unbounded payload really is oversized

    bounded = bound_attributes(raw)
    bounded_size = len(json.dumps(bounded, default=str).encode("utf-8"))
    assert bounded_size <= 16384


def test_moderately_oversized_payload_is_compacted_not_just_summarized():
    # A payload just over the limit should get the "compact()" treatment
    # (truncated lists/strings, a count of omitted items) rather than
    # immediately falling back to the bare "too large" summary.
    payload = {"items": [{"id": i, "note": "x" * 50} for i in range(400)]}
    bounded = bound_attributes(payload, max_bytes=12_000)
    assert bounded.get("truncated") is not True or "items" in bounded
    size = len(json.dumps(bounded, default=str).encode("utf-8"))
    assert size <= 12_000


def _realistic_device_model_row(i: int) -> dict:
    """Field-for-field the same shape device_model.py's build() actually
    produces (~28 keys, two nested structures) -- not the older test's
    flat, 6-field synthetic device."""
    return {
        "id": f"mac:aa:bb:cc:dd:ee:{i:02x}", "name": f"GigaCore {i}",
        "ip": f"10.4.{i // 254}.{i % 254}", "ipv6": None, "mac": f"aa:bb:cc:dd:ee:{i:02x}",
        "serial": f"SN{i:06d}", "manufacturer": "Luminex", "model": "GigaCore 10",
        "firmware": "3.5.1", "category": "switch", "location": "Rack 3", "role": "network",
        "interface": "enp10s0", "vlan": 10, "switch_name": "Core", "switch_port": i % 24,
        "link_speed_mbps": 1000,
        "protocols": ["sACN", "Art-Net", "SNMP"], "sources": ["mdns", "lldp"],
        "evidence_sources": ["mdns", "lldp", "snmp"], "confidence": "confirmed",
        "confidence_score": 0.95, "first_seen": 1000.0 + i, "last_seen": 2000.0 + i,
        "topology_nodes": [f"node:{i}"], "topology_links": 2,
        "physical_links": [
            {"peer_id": f"node:{i+1}", "local_port": 1, "peer_port": 2, "vlan": 10,
             "link_speed_mbps": 1000, "protocol": "LLDP", "confidence": "confirmed",
             "evidence": ["lldp"], "health": "ok"},
        ],
        "physical_path": {"interface": "enp10s0", "vlan": 10, "switch": "Core",
                           "port": i % 24, "link_speed_mbps": 1000},
        "monitor_mode": "auto",
    }


def test_real_shaped_device_list_with_54_devices_keeps_real_data_not_just_a_sentinel():
    """Regression test for a real production finding: a live installation
    with 54 real devices (this exact field shape, from device_model.py's
    own build()) got its ENTIRE devices list replaced by the bare
    {"truncated": True, "message": ...} sentinel -- zero devices survived,
    breaking every feature reading this list, including the network
    topology panel's own per-interface filter. The single-pass compact()
    (list capped at 20 items) wasn't enough for this richer, nested shape
    even after truncating to 20 devices, and the old code gave up
    entirely the moment that one pass didn't fit. Confirms the fix keeps
    genuine device rows (fewer than 54, but not zero)."""
    payload = {"devices": [_realistic_device_model_row(i) for i in range(54)]}
    raw_size = len(json.dumps(payload, default=str).encode("utf-8"))
    assert raw_size > 12_000  # sanity check: this really does need compaction

    bounded = bound_attributes(payload, max_bytes=12_000)
    assert bounded.get("truncated") is not True, "must not have given up entirely -- this is the exact production bug"
    assert "devices" in bounded
    assert len(bounded["devices"]) > 0, "at least some real devices must survive compaction"
    # Confirms these are genuine device rows, not just count markers.
    assert bounded["devices"][0].get("name", "").startswith("GigaCore")
    size = len(json.dumps(bounded, default=str).encode("utf-8"))
    assert size <= 12_000


def test_old_single_pass_compaction_would_have_failed_this_exact_payload():
    """Negative proof, not just a positive one: reproduces the OLD
    compact() (fixed 20/40/512 limits, single attempt) against the same
    realistic 54-device payload, confirming it genuinely does overflow
    and would have fallen back to the empty sentinel -- this isn't a
    strawman, the old code really did fail on this shape."""
    def old_compact(obj, depth=0):
        if depth >= 5:
            return "<truncated>"
        if isinstance(obj, dict):
            items = list(obj.items())
            out = {str(k): old_compact(v, depth + 1) for k, v in items[:40]}
            if len(items) > 40:
                out["_omitted_keys"] = len(items) - 40
            return out
        if isinstance(obj, (list, tuple)):
            out = [old_compact(v, depth + 1) for v in obj[:20]]
            if len(obj) > 20:
                out.append({"_omitted_items": len(obj) - 20})
            return out
        if isinstance(obj, str) and len(obj) > 512:
            return obj[:509] + "..."
        return obj

    payload = {"devices": [_realistic_device_model_row(i) for i in range(54)]}
    old_result = old_compact(payload)
    old_size = len(json.dumps(old_result, default=str).encode("utf-8"))
    assert old_size > 12_000, "the old single-pass compaction should still overflow for this realistic shape"
