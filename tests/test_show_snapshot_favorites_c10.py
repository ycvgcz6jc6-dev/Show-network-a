"""Phase C10 (rapport maître, S100): "Les favoris deviennent le périmètre
privilégié de Doctor/Incident/History." compare() cross-references its
diffs against the *current* device_model's monitor_mode, tagging
favorite_related on device-level diffs (missing/new/fact-changed).
"""
from __future__ import annotations

from custom_components.dmx_monitor.show_snapshot import ShowSnapshotManager


def test_missing_favorite_device_is_tagged(tmp_path):
    m = ShowSnapshotManager(str(tmp_path))
    baseline = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "monitor_mode": "monitor"},
        {"id": "mac:bb", "name": "Autre appareil", "ip": "10.4.1.9", "monitor_mode": "auto"},
    ]}, "dmx_universe_matrix": []}
    m.create("Baseline", baseline)

    # Both devices vanish from the current state; only "mac:aa" is a favorite.
    current = {"device_model": {"devices": []}, "dmx_universe_matrix": []}
    result = m.compare(current)

    by_label = {d["label"]: d for d in result["differences"] if d["kind"] == "device_missing"}
    assert by_label["GigaCore"]["favorite_related"] is True
    assert by_label["Autre appareil"]["favorite_related"] is False
    assert result["favorite_difference_count"] == 1


def test_new_and_changed_favorite_devices_are_tagged(tmp_path):
    m = ShowSnapshotManager(str(tmp_path))
    baseline = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "firmware": "1.0", "monitor_mode": "monitor"},
    ]}, "dmx_universe_matrix": []}
    m.create("Baseline", baseline)

    current = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "firmware": "2.0", "monitor_mode": "monitor"},  # changed
        {"id": "mac:cc", "name": "Nouvel appareil", "ip": "10.4.1.50", "monitor_mode": "monitor"},  # new, also a favorite
    ]}, "dmx_universe_matrix": []}
    result = m.compare(current)

    changed = next(d for d in result["differences"] if d["kind"] == "device_fact_changed")
    assert changed["label"] == "GigaCore"
    assert changed["favorite_related"] is True

    new = next(d for d in result["differences"] if d["kind"] == "device_new")
    assert new["label"] == "Nouvel appareil"
    assert new["favorite_related"] is True

    assert result["favorite_difference_count"] == 2


def test_favorite_status_is_read_from_current_state_when_device_still_present(tmp_path):
    """A device that was NOT a favorite when the reference snapshot was
    taken, but has since been starred, must still be tagged when it's
    still present in the current state -- favorite status is a live
    preference, not a fact worth freezing into an old snapshot."""
    m = ShowSnapshotManager(str(tmp_path))
    baseline = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "firmware": "1.0", "monitor_mode": "auto"},  # not a favorite yet
    ]}, "dmx_universe_matrix": []}
    m.create("Baseline", baseline)

    current = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "firmware": "2.0", "monitor_mode": "monitor"},  # starred since
    ]}, "dmx_universe_matrix": []}
    result = m.compare(current)
    changed = next(d for d in result["differences"] if d["kind"] == "device_fact_changed")
    assert changed["favorite_related"] is True, "favorite status must reflect the CURRENT device_model, not the frozen reference"


def test_no_favorites_leaves_every_diff_untagged(tmp_path):
    m = ShowSnapshotManager(str(tmp_path))
    baseline = {"device_model": {"devices": [
        {"id": "mac:aa", "name": "GigaCore", "ip": "10.4.1.3", "monitor_mode": "auto"},
    ]}, "dmx_universe_matrix": []}
    m.create("Baseline", baseline)
    current = {"device_model": {"devices": []}, "dmx_universe_matrix": []}
    result = m.compare(current)
    assert all(not d.get("favorite_related") for d in result["differences"])
    assert result["favorite_difference_count"] == 0
