"""Evidence-only Flight Recorder analysis for Show Network.

This module never invents root causes. It groups temporally-close journal events
and exposes correlations so an operator can answer "what happened around this
incident?" from facts already recorded by Show Network.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from typing import Any

_ERROR_WORDS = ("failed", "error", "lost", "blocked", "timeout", "drift", "injection")
_WARN_WORDS = ("change", "stale", "warning", "degraded", "priority_change", "cid_change")
_RECOVERY_WORDS = ("recovered", "restore", "online", "seen")


def _epoch(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def classify(event: dict[str, Any]) -> str:
    name = str(event.get("event") or "").lower()
    if any(w in name for w in _ERROR_WORDS):
        return "error"
    if any(w in name for w in _WARN_WORDS):
        return "warning"
    if any(w in name for w in _RECOVERY_WORDS):
        return "recovery"
    return "info"


def analyze(events: list[dict[str, Any]], *, window_s: float = 20.0, limit: int = 100) -> dict[str, Any]:
    """Return bounded timeline + incident correlations from journal events."""
    cleaned = []
    for raw in list(events or [])[-limit:]:
        if not isinstance(raw, dict):
            continue
        item = {"ts": raw.get("ts"), "kind": str(raw.get("kind") or "general")[:40],
                "event": str(raw.get("event") or "unknown")[:200], "data": raw.get("data") or {}}
        item["severity"] = classify(item)
        item["epoch"] = _epoch(item["ts"])
        cleaned.append(item)
    cleaned.sort(key=lambda x: (x["epoch"] is None, x["epoch"] or 0))

    incidents = []
    anchors = [e for e in cleaned if e["severity"] in ("error", "warning")]
    for anchor in anchors[-12:]:
        at = anchor["epoch"]
        if at is None:
            related = [anchor]
        else:
            related = [e for e in cleaned if e["epoch"] is not None and abs(e["epoch"] - at) <= window_s]
        kinds = sorted({e["kind"] for e in related})
        # Facts only: this is deliberately called "observed together", not cause.
        incidents.append({
            "ts": anchor["ts"], "severity": anchor["severity"], "kind": anchor["kind"],
            "event": anchor["event"], "data": anchor["data"], "window_s": window_s,
            "related_count": len(related), "related_kinds": kinds,
            "related_events": [{k: e[k] for k in ("ts", "kind", "event", "severity", "data")} for e in related[-30:]],
        })

    counts = Counter(e["severity"] for e in cleaned)
    kind_counts = Counter(e["kind"] for e in cleaned)
    last_incident = incidents[-1] if incidents else None
    return {
        "events_total": len(cleaned), "window_s": window_s,
        "severity_counts": dict(counts), "kind_counts": dict(kind_counts),
        "timeline": [{k: e[k] for k in ("ts", "kind", "event", "severity", "data")} for e in cleaned],
        "incidents": incidents,
        "last_incident": last_incident,
        "explanation": "Corrélations temporelles uniquement : les événements proches ne sont pas présentés comme une cause.",
    }
