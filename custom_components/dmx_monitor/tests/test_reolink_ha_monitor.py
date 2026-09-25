"""Tests for reolink_ha_monitor.py -- reads Home Assistant's own
official `reolink` integration entities. Entity naming (binary_sensor.
<camera>_motion/_person/_vehicle/_pet/_animal/_visitor/_package) is
taken directly from Home Assistant's own integration documentation
(home-assistant.io/integrations/reolink/), not guessed.
"""
from __future__ import annotations

from homeassistant.helpers import entity_registry as er

from custom_components.dmx_monitor.reolink_ha_monitor import ReolinkHAMonitor


class _FakeEntry:
    def __init__(self, entity_id, platform, device_id):
        self.entity_id = entity_id
        self.platform = platform
        self.device_id = device_id


class _FakeRegistry:
    def __init__(self, entries):
        self.entities = {e.entity_id: e for e in entries}


class _FakeState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class _FakeStates:
    def __init__(self, table):
        self._table = table

    def get(self, entity_id):
        return self._table.get(entity_id)


class _FakeHass:
    def __init__(self, states_table):
        self.states = _FakeStates(states_table)


def _install_fake_registry(monkeypatch, entries):
    registry = _FakeRegistry(entries)
    monkeypatch.setattr(er, "async_get", lambda hass: registry)


def test_no_reolink_cameras_reports_empty_list(monkeypatch):
    _install_fake_registry(monkeypatch, [])
    monitor = ReolinkHAMonitor(_FakeHass({}))
    snap = monitor.snapshot()
    assert snap["available"] is True
    assert snap["cameras"] == []
    assert snap["camera_count"] == 0


def test_camera_with_motion_and_person_detection(monkeypatch):
    entries = [
        _FakeEntry("camera.backstage_left", "reolink", "dev1"),
        _FakeEntry("binary_sensor.backstage_left_motion", "reolink", "dev1"),
        _FakeEntry("binary_sensor.backstage_left_person", "reolink", "dev1"),
    ]
    _install_fake_registry(monkeypatch, entries)
    states = {
        "camera.backstage_left": _FakeState("streaming", {"friendly_name": "Backstage Left"}),
        "binary_sensor.backstage_left_motion": _FakeState("on"),
        "binary_sensor.backstage_left_person": _FakeState("off"),
    }
    monitor = ReolinkHAMonitor(_FakeHass(states))
    snap = monitor.snapshot()
    assert snap["camera_count"] == 1
    cam = snap["cameras"][0]
    assert cam["name"] == "Backstage Left"
    assert cam["state"] == "streaming"
    assert cam["available"] is True
    detections = {d["kind"]: d for d in cam["detections"]}
    assert detections["motion"]["active"] is True
    assert detections["person"]["active"] is False


def test_non_reolink_entities_are_ignored(monkeypatch):
    """A camera or binary_sensor from a *different* integration must
    never be mistaken for a Reolink one -- correlation is by the
    entity registry's own platform field, not by naming pattern alone."""
    entries = [
        _FakeEntry("camera.front_door", "generic_camera", "devX"),
        _FakeEntry("binary_sensor.front_door_motion", "generic_camera", "devX"),
        _FakeEntry("camera.stage_left", "reolink", "dev1"),
    ]
    _install_fake_registry(monkeypatch, entries)
    states = {"camera.stage_left": _FakeState("idle")}
    monitor = ReolinkHAMonitor(_FakeHass(states))
    snap = monitor.snapshot()
    assert snap["camera_count"] == 1
    assert snap["cameras"][0]["entity_id"] == "camera.stage_left"


def test_unavailable_camera_reported_correctly(monkeypatch):
    entries = [_FakeEntry("camera.backstage_left", "reolink", "dev1")]
    _install_fake_registry(monkeypatch, entries)
    states = {"camera.backstage_left": _FakeState("unavailable")}
    monitor = ReolinkHAMonitor(_FakeHass(states))
    cam = monitor.snapshot()["cameras"][0]
    assert cam["available"] is False
    assert cam["state"] == "unavailable"


def test_camera_with_no_state_yet_reported_gracefully(monkeypatch):
    """The entity is registered but hass.states has nothing for it yet
    (e.g. right at startup) -- must not crash."""
    entries = [_FakeEntry("camera.backstage_left", "reolink", "dev1")]
    _install_fake_registry(monkeypatch, entries)
    monitor = ReolinkHAMonitor(_FakeHass({}))
    cam = monitor.snapshot()["cameras"][0]
    assert cam["state"] is None
    assert cam["available"] is False
    assert cam["name"] == "camera.backstage_left"  # falls back to entity_id


def test_multiple_cameras_and_detection_kinds_all_official_types(monkeypatch):
    """Confirms all seven documented detection types are handled, not
    just motion/person."""
    entries = [
        _FakeEntry("camera.doorbell", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_motion", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_person", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_vehicle", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_pet", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_animal", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_visitor", "reolink", "dev2"),
        _FakeEntry("binary_sensor.doorbell_package", "reolink", "dev2"),
    ]
    _install_fake_registry(monkeypatch, entries)
    states = {"camera.doorbell": _FakeState("idle")}
    for kind in ("motion", "person", "vehicle", "pet", "animal", "visitor", "package"):
        states[f"binary_sensor.doorbell_{kind}"] = _FakeState("off")
    monitor = ReolinkHAMonitor(_FakeHass(states))
    cam = monitor.snapshot()["cameras"][0]
    kinds = {d["kind"] for d in cam["detections"]}
    assert kinds == {"motion", "person", "vehicle", "pet", "animal", "visitor", "package"}
