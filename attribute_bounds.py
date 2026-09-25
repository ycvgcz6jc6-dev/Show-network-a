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
    ``value``, preserving as much useful diagnostic detail as fits.

    AUDIT FIX (confirmed live: sensor.equipements_consolides_consolidated_
    devices, 54 real devices, entirely replaced by the "truncated" sentinel
    -- attributes carried none of the 54 devices at all, breaking every
    feature reading this sensor's device list, including the network
    topology panel's own per-interface filter). The single compaction pass
    below (list/dict limits chosen once) can still exceed max_bytes for a
    genuinely large payload -- a device row here has ~28 fields, several
    themselves nested lists/dicts, so 20 kept devices can still overflow
    12KB. The previous version gave up entirely the moment that first pass
    wasn't enough, discarding 100% of the data. Now retries with
    progressively smaller list/dict/string limits before ever falling back
    to the empty sentinel, so a genuinely oversized payload degrades to
    "fewer devices, fully shown" rather than "no devices at all".
    """

    def size(obj: Any) -> int:
        try:
            return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            return max_bytes + 1

    if size(value) <= max_bytes:
        return value

    def compact(obj: Any, *, list_limit: int, dict_limit: int, str_limit: int, depth: int = 0) -> Any:
        if depth >= 5:
            return "<truncated>"
        if isinstance(obj, dict):
            items = list(obj.items())
            out = {str(k): compact(v, list_limit=list_limit, dict_limit=dict_limit, str_limit=str_limit, depth=depth + 1) for k, v in items[:dict_limit]}
            if len(items) > dict_limit:
                out["_omitted_keys"] = len(items) - dict_limit
            return out
        if isinstance(obj, (list, tuple)):
            out = [compact(v, list_limit=list_limit, dict_limit=dict_limit, str_limit=str_limit, depth=depth + 1) for v in obj[:list_limit]]
            if len(obj) > list_limit:
                out.append({"_omitted_items": len(obj) - list_limit})
            return out
        if isinstance(obj, str) and len(obj) > str_limit:
            return obj[:max(0, str_limit - 3)] + "..."
        return obj

    # Each retry roughly halves how much is kept at every level. A payload
    # that's mostly "many similar rows" (the common shape here: a device
    # list, a check list, an incident list) shrinks close to linearly with
    # list_limit, so this converges quickly without needing many steps.
    compacted = None
    for list_limit, dict_limit, str_limit in (
        (20, 40, 512), (10, 25, 256), (5, 15, 128), (2, 8, 64), (1, 5, 32),
    ):
        compacted = compact(value, list_limit=list_limit, dict_limit=dict_limit, str_limit=str_limit)
        if size(compacted) <= max_bytes:
            break

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
