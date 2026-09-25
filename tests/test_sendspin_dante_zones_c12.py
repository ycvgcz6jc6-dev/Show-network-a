"""Reads spin2dante's own Music Assistant media_player entities via
hass.states -- verified live against a real installation (see module
docstring in sendspin_dante_zones.py). Fixture shapes below mirror the
exact live attribute set observed: active_queue, app_id, device_class,
group_members, is_volume_muted, mass_player_type, volume_level, etc.
"""
from __future__ import annotations

from custom_components.dmx_monitor.sendspin_dante_zones import SendspinDanteZoneMonitor


class _FakeState:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes


class _FakeStates:
    def __init__(self, table):
        self._table = table

    def get(self, entity_id):
        return self._table.get(entity_id)


class _FakeHass:
    def __init__(self, table):
        self.states = _FakeStates(table)


def test_idle_zone_reports_not_active():
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("idle", {
            "friendly_name": "home-assistance-to-bureau", "app_id": "music_assistant",
            "volume_level": 0.75, "is_volume_muted": False,
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bureau"])
    rows = monitor.snapshot()
    assert rows == [{
        "entity_id": "media_player.home_assistance_to_bureau",
        "name": "home-assistance-to-bureau", "found": True,
        "state": "idle", "active": False, "volume_level": 0.75, "muted": False,
        "dante_subscriber_status": None, "dante_subscriber_status_verified": False,
    }]


def test_playing_zone_reports_active():
    hass = _FakeHass({
        "media_player.home_assistance_to_bar": _FakeState("playing", {
            "friendly_name": "home-assistance-to-bar", "app_id": "music_assistant",
            "volume_level": 0.70, "is_volume_muted": False,
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bar"])
    row = monitor.snapshot()[0]
    assert row["active"] is True
    assert row["state"] == "playing"
    assert row["volume_level"] == 0.70


def test_missing_entity_reported_as_not_found_not_a_crash():
    """The user configures which entity_ids to watch; a typo or a zone
    that was removed must degrade gracefully, not raise."""
    hass = _FakeHass({})
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.does_not_exist"])
    rows = monitor.snapshot()
    assert rows == [{
        "entity_id": "media_player.does_not_exist", "name": "media_player.does_not_exist",
        "found": False, "state": None, "active": False, "volume_level": None, "muted": None,
        "dante_subscriber_status": None, "dante_subscriber_status_verified": False,
    }]


def test_multiple_zones_independent():
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("idle", {"friendly_name": "Bureau", "volume_level": 0.75, "is_volume_muted": False}),
        "media_player.home_assistance_to_bar": _FakeState("playing", {"friendly_name": "Bar", "volume_level": 0.70, "is_volume_muted": False}),
    })
    monitor = SendspinDanteZoneMonitor(hass, [
        "media_player.home_assistance_to_bureau",
        "media_player.home_assistance_to_bar",
        "media_player.does_not_exist",
    ])
    rows = monitor.snapshot()
    assert len(rows) == 3
    by_id = {r["entity_id"]: r for r in rows}
    assert by_id["media_player.home_assistance_to_bureau"]["active"] is False
    assert by_id["media_player.home_assistance_to_bar"]["active"] is True
    assert by_id["media_player.does_not_exist"]["found"] is False


def test_muted_zone_reports_muted_true():
    hass = _FakeHass({
        "media_player.home_assistance_to_test": _FakeState("playing", {
            "friendly_name": "Test", "volume_level": 0.5, "is_volume_muted": True,
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_test"])
    assert monitor.snapshot()[0]["muted"] is True


def test_no_entities_configured_returns_empty_list():
    monitor = SendspinDanteZoneMonitor(_FakeHass({}), [])
    assert monitor.snapshot() == []


def test_name_falls_back_to_entity_id_when_no_friendly_name():
    hass = _FakeHass({
        "media_player.nameless": _FakeState("idle", {}),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.nameless"])
    assert monitor.snapshot()[0]["name"] == "media_player.nameless"


def test_dante_subscriber_status_synchronized_is_surfaced():
    """Candidate field: exact string from spin2dante's own docs, only
    surfaced if the source attribute matches exactly -- not yet
    confirmed against a live read with report_dante_subscriber
    actually enabled (see module docstring)."""
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("playing", {
            "friendly_name": "Bureau", "source": "Synchronized",
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bureau"])
    row = monitor.snapshot()[0]
    assert row["dante_subscriber_status"] == "Synchronized"
    assert row["dante_subscriber_status_verified"] is False


def test_dante_subscriber_status_external_source_is_surfaced():
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("playing", {
            "friendly_name": "Bureau", "source": "ExternalSource",
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bureau"])
    assert monitor.snapshot()[0]["dante_subscriber_status"] == "ExternalSource"


def test_dante_subscriber_status_none_when_source_is_something_else():
    """The default, currently-observed value ("Music Assistant Queue")
    must NOT be misread as either Dante-subscription state -- only the
    two exact documented strings are ever surfaced."""
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("playing", {
            "friendly_name": "Bureau", "source": "Music Assistant Queue",
        }),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bureau"])
    assert monitor.snapshot()[0]["dante_subscriber_status"] is None


def test_dante_subscriber_status_none_when_source_attribute_absent():
    hass = _FakeHass({
        "media_player.home_assistance_to_bureau": _FakeState("playing", {"friendly_name": "Bureau"}),
    })
    monitor = SendspinDanteZoneMonitor(hass, ["media_player.home_assistance_to_bureau"])
    assert monitor.snapshot()[0]["dante_subscriber_status"] is None
