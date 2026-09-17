"""Shared helper: bound a value's JSON-serialized size for HA Recorder.

Home Assistant Recorder rejects entity state attributes larger than 16384
bytes. This was originally a private helper inside sensor.py, called
directly from each entity's ``extra_state_attributes`` property -- which
meant its (potentially expensive: a full ``json.dumps()`` of a nested
structure, sometimes twice) computation ran on *every* attribute read, not
once per actual data update. An audited installation found
``sensor.diagnostics_reception_protocoles_protocol_receive_diagnostics``
taking ~0.6s per update because of this.

Moved here (a module neither sensor.py nor coordinator.py already depends
on, avoiding a circular import) so coordinator.py can precompute the
bounded form once per refresh cycle -- see coordinator.py's
_async_update_data, which now calls this via hass.async_add_executor_job
for the handful of keys large enough to matter -- and sensor.py's
properties become a cheap dict lookup instead of redoing this work on
every single read.
"""
from __future__ import annotations

import json
from typing import Any


def bound_attributes(value: Any, max_bytes: int = 12_000) -> Any:
    """Return a Recorder-safe (<= max_bytes when JSON-serialized) form of
    ``value``, preserving as much useful diagnostic detail as fits."""

    def size(obj: Any) -> int:
        try:
            return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            return max_bytes + 1

    if size(value) <= max_bytes:
        return value

    def compact(obj: Any, depth: int = 0) -> Any:
        if depth >= 5:
            return "<truncated>"
        if isinstance(obj, dict):
            items = list(obj.items())
            out = {str(k): compact(v, depth + 1) for k, v in items[:40]}
            if len(items) > 40:
                out["_omitted_keys"] = len(items) - 40
            return out
        if isinstance(obj, (list, tuple)):
            out = [compact(v, depth + 1) for v in obj[:20]]
            if len(obj) > 20:
                out.append({"_omitted_items": len(obj) - 20})
            return out
        if isinstance(obj, str) and len(obj) > 512:
            return obj[:509] + "..."
        return obj

    compacted = compact(value)
    if size(compacted) > max_bytes:
        return {
            "truncated": True,
            "original_bytes": size(value),
            "message": "Diagnostics too large for Home Assistant Recorder; full live data remains in Show Network.",
        }
    if isinstance(compacted, dict):
        compacted["_truncated_for_recorder"] = True
        compacted["_original_bytes"] = size(value)
    return compacted
