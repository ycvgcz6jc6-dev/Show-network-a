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
