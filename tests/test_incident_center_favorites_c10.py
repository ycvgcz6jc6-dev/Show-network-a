"""Phase C10 (rapport maître, S100): incidents touching a favorited
(monitor_mode='monitor') device get tagged favorite_related, so a
dashboard can surface them first -- the `devices` parameter build()
already accepted but never read.
"""
from __future__ import annotations

import tempfile

from custom_components.dmx_monitor.incident_center import IncidentCenter


def _recorder_with_incident(device_ids, kind="ptp", event="clock_lost", ts="2026-09-23T10:00:00+00:00"):
    return {
        "timeline": [],
        "incidents": [
            {
                "ts": ts, "severity": "error", "kind": kind, "event": event,
                "related_device_ids": device_ids,
                "related_events": [{"kind": kind, "event": event}],
            }
        ],
    }


def _device_model(favorite_ids, other_ids=()):
    devices = [{"id": i, "monitor_mode": "monitor"} for i in favorite_ids]
    devices += [{"id": i, "monitor_mode": "auto"} for i in other_ids]
    return {"devices": devices}


def test_incident_touching_a_favorite_is_tagged():
    with tempfile.TemporaryDirectory() as tmp:
        center = IncidentCenter(tmp)
        recorder = _recorder_with_incident(["mac:aabbcc"])
        result = center.build(recorder, _device_model(favorite_ids=["mac:aabbcc"]))
        assert result["incidents"][0]["favorite_related"] is True
        assert result["favorite_active_count"] == 1


def test_incident_not_touching_a_favorite_is_not_tagged():
    with tempfile.TemporaryDirectory() as tmp:
        center = IncidentCenter(tmp)
        recorder = _recorder_with_incident(["mac:zzzzzz"])
        result = center.build(recorder, _device_model(favorite_ids=["mac:aabbcc"]))
        assert result["incidents"][0]["favorite_related"] is False
        assert result["favorite_active_count"] == 0


def test_no_device_model_does_not_crash_and_tags_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        center = IncidentCenter(tmp)
        recorder = _recorder_with_incident(["mac:aabbcc"])
        result = center.build(recorder, None)  # devices omitted entirely, as before this fix
        assert result["incidents"][0]["favorite_related"] is False
        assert result["favorite_active_count"] == 0


def test_favorite_active_count_ignores_resolved_incidents():
    with tempfile.TemporaryDirectory() as tmp:
        center = IncidentCenter(tmp)
        recorder = {
            "timeline": [{"severity": "recovery", "kind": "ptp", "ts": "2026-09-23T10:05:00+00:00"}],
            "incidents": [
                {
                    "ts": "2026-09-23T10:00:00+00:00", "severity": "error", "kind": "ptp", "event": "clock_lost",
                    "related_device_ids": ["mac:aabbcc"],
                    "related_events": [{"kind": "ptp", "event": "clock_lost"}],
                },
            ],
        }
        result = center.build(recorder, _device_model(favorite_ids=["mac:aabbcc"]))
        assert result["incidents"][0]["status"] == "RESOLVED"
        assert result["incidents"][0]["favorite_related"] is True
        assert result["favorite_active_count"] == 0, "a resolved incident must not count toward the active favorite total"


def test_all_other_incident_fields_unaffected():
    """Guards against the favorite tagging accidentally changing anything
    else about how an incident is built."""
    with tempfile.TemporaryDirectory() as tmp:
        center = IncidentCenter(tmp)
        recorder = _recorder_with_incident(["mac:aabbcc"])
        result = center.build(recorder, _device_model(favorite_ids=["mac:aabbcc"]))
        incident = result["incidents"][0]
        assert incident["severity"] == "error"
        assert incident["device_ids"] == ["mac:aabbcc"]
        assert incident["status"] == "ACTIVE"
        assert result["incident_count"] == 1
        assert result["active_count"] == 1
