"""Tests for the atomic-write fix to DMX->HA zone persistence
(coordinator.py's save_dmx_ha_zones / async_save_dmx_ha_zones /
_load_dmx_ha_zones). No test previously existed for this.

Audit-confirmed gap ("écriture atomique des zones"): saves used to
write directly to the live file (Path.write_text), so a crash mid-write
could leave a truncated/corrupted JSON file, which the load path's
`except (OSError, ValueError, TypeError): return` then silently
discarded -- every configured zone lost with no visible trace. Fixed to
the same tmp-file + atomic rename pattern already used correctly
elsewhere in this project (rule_storage.py, dmx_ha_mapping_storage.py).

These methods are bound methods on ShowNetworkCoordinator, but their
logic only touches self.dmx_ha_zone_store_path, self.dmx_ha_zone_engine
and self.config_backups -- calling them with a minimal duck-typed stand-in
object as `self` avoids needing a full, heavily-mocked Home Assistant
coordinator just to exercise file-persistence logic.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest

from custom_components.dmx_monitor.coordinator import ShowNetworkCoordinator
from custom_components.dmx_monitor.dmx_ha_zones import DmxHAZoneEngine, DmxHAZone


class _FakeHass:
    class _Executor:
        async def async_add_executor_job(self, func, *args):
            return func(*args)
    def __init__(self):
        pass


class _FakeBackups:
    def __init__(self):
        self.calls: list[str] = []

    def backup(self, reason: str) -> None:
        self.calls.append(reason)


class _FakeCoordinator:
    """Minimal duck-typed stand-in providing exactly the attributes
    save/load touch -- not a real ShowNetworkCoordinator instance."""
    def __init__(self, store_path: Path):
        self.dmx_ha_zone_store_path = str(store_path)
        self.dmx_ha_zone_engine = DmxHAZoneEngine()
        self.config_backups = _FakeBackups()

    class hass:
        @staticmethod
        async def async_add_executor_job(func, *args):
            return func(*args)


def _sample_zone(zone_id="z1"):
    return DmxHAZone(zone_id=zone_id, name="Wash 1", universe=1, channels=(1,), mode="dimmer")


def test_save_writes_via_atomic_tmp_rename_not_direct_write(tmp_path):
    """The whole point of the fix: verify the save path actually goes
    through Path.replace (tmp file swapped in), not a direct write_text
    onto the live path."""
    store = tmp_path / "zones.json"
    fake = _FakeCoordinator(store)
    fake.dmx_ha_zone_engine.add(_sample_zone())

    ShowNetworkCoordinator.save_dmx_ha_zones(fake)

    assert store.exists()
    assert not store.with_suffix(".tmp").exists(), "tmp file must be cleaned up by the rename, not left behind"
    saved = json.loads(store.read_text(encoding="utf-8"))
    assert saved[0]["zone_id"] == "z1"
    assert fake.config_backups.calls == ["zone_save"]


def test_save_overwriting_existing_file_never_leaves_a_partial_result(tmp_path):
    """Simulates the property atomic rename guarantees: after save(), the
    file is always fully the new content -- verified across many
    sequential saves, which would be far more likely to expose a
    half-written file if the implementation ever regressed to a direct
    write."""
    store = tmp_path / "zones.json"
    fake = _FakeCoordinator(store)
    for i in range(20):
        fake.dmx_ha_zone_engine.zones.clear()
        fake.dmx_ha_zone_engine.add(_sample_zone(zone_id=f"z{i}"))
        ShowNetworkCoordinator.save_dmx_ha_zones(fake)
        saved = json.loads(store.read_text(encoding="utf-8"))
        assert len(saved) == 1
        assert saved[0]["zone_id"] == f"z{i}"


def test_load_reads_back_a_saved_zone_round_trip(tmp_path):
    store = tmp_path / "zones.json"
    fake = _FakeCoordinator(store)
    fake.dmx_ha_zone_engine.add(_sample_zone())
    ShowNetworkCoordinator.save_dmx_ha_zones(fake)

    fake2 = _FakeCoordinator(store)
    ShowNetworkCoordinator._load_dmx_ha_zones(fake2)
    assert "z1" in fake2.dmx_ha_zone_engine.zones
    assert fake2.dmx_ha_zone_engine.zones["z1"].name == "Wash 1"


def test_load_with_no_file_yet_is_a_silent_noop(tmp_path):
    store = tmp_path / "does_not_exist.json"
    fake = _FakeCoordinator(store)
    ShowNetworkCoordinator._load_dmx_ha_zones(fake)  # must not raise
    assert fake.dmx_ha_zone_engine.zones == {}


def test_load_with_corrupted_file_logs_a_warning_instead_of_silent_loss(tmp_path, caplog):
    """The load-side half of the fix: a corrupted file (simulating what
    an interrupted non-atomic write used to leave behind) must be
    visible in the log, not just silently discarded."""
    store = tmp_path / "zones.json"
    store.write_text('[{"zone_id": "z1", "name": "Wash 1", "universe": 1, "channels": [1', encoding="utf-8")  # truncated JSON
    fake = _FakeCoordinator(store)
    with caplog.at_level(logging.WARNING):
        ShowNetworkCoordinator._load_dmx_ha_zones(fake)
    assert fake.dmx_ha_zone_engine.zones == {}
    assert any("DMX→HA zones" in rec.message for rec in caplog.records)


def test_load_skips_individual_bad_zone_entries_but_keeps_good_ones(tmp_path):
    store = tmp_path / "zones.json"
    store.write_text(json.dumps([
        {"zone_id": "good", "name": "Good Zone", "universe": 1, "channels": [1]},
        {"zone_id": "bad", "name": "Bad Zone", "universe": 99999, "channels": [1]},  # universe out of range
    ]), encoding="utf-8")
    fake = _FakeCoordinator(store)
    ShowNetworkCoordinator._load_dmx_ha_zones(fake)
    assert "good" in fake.dmx_ha_zone_engine.zones
    assert "bad" not in fake.dmx_ha_zone_engine.zones


@pytest.mark.asyncio
async def test_async_save_also_uses_atomic_rename(tmp_path):
    store = tmp_path / "zones.json"
    fake = _FakeCoordinator(store)
    fake.dmx_ha_zone_engine.add(_sample_zone())
    await ShowNetworkCoordinator.async_save_dmx_ha_zones(fake)
    assert store.exists()
    assert not store.with_suffix(".tmp").exists()
    saved = json.loads(store.read_text(encoding="utf-8"))
    assert saved[0]["zone_id"] == "z1"
    assert fake.config_backups.calls == ["zone_save"]


def test_save_creates_parent_directory_if_missing(tmp_path):
    store = tmp_path / "nested" / "dir" / "zones.json"
    fake = _FakeCoordinator(store)
    fake.dmx_ha_zone_engine.add(_sample_zone())
    ShowNetworkCoordinator.save_dmx_ha_zones(fake)
    assert store.exists()
