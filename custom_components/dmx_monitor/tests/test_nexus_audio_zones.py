"""Tests for nexus_audio_zones.py -- the lightweight, spin2dante-style
alternative to nexus_audio_monitor.py's direct HTTP client. Same
mechanism and same test shape as test_sendspin_dante_zones_c12.py,
since both read ordinary Home Assistant media_player entity state.
"""
from __future__ import annotations

from custom_components.dmx_monitor.nexus_audio_zones import NexusAudioZoneMonitor


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


def test_idle_source_reports_not_active():
    hass = _FakeHass({
        "media_player.shure_dante_rx": _FakeState("idle", {
            "friendly_name": "Shure Dante RX", "volume_level": 0.8, "is_volume_muted": False,
        }),
    })
    monitor = NexusAudioZoneMonitor(hass, ["media_player.shure_dante_rx"])
    row = monitor.snapshot()[0]
    assert row["active"] is False
    assert row["state"] == "idle"
    assert row["volume_level"] == 0.8


def test_playing_source_reports_active():
    hass = _FakeHass({
        "media_player.airplay_in": _FakeState("playing", {
            "friendly_name": "AirPlay In", "volume_level": 0.6, "is_volume_muted": False,
        }),
    })
    monitor = NexusAudioZoneMonitor(hass, ["media_player.airplay_in"])
    row = monitor.snapshot()[0]
    assert row["active"] is True


def test_missing_entity_reported_as_not_found_not_a_crash():
    hass = _FakeHass({})
    monitor = NexusAudioZoneMonitor(hass, ["media_player.does_not_exist"])
    row = monitor.snapshot()[0]
    assert row["found"] is False
    assert row["state"] is None


def test_multiple_sources_tracked_independently():
    hass = _FakeHass({
        "media_player.shure_dante_rx": _FakeState("idle", {"friendly_name": "Shure", "volume_level": 0.5, "is_volume_muted": False}),
        "media_player.airplay_in": _FakeState("playing", {"friendly_name": "AirPlay", "volume_level": 0.6, "is_volume_muted": False}),
    })
    monitor = NexusAudioZoneMonitor(hass, ["media_player.shure_dante_rx", "media_player.airplay_in"])
    rows = {r["entity_id"]: r for r in monitor.snapshot()}
    assert rows["media_player.shure_dante_rx"]["active"] is False
    assert rows["media_player.airplay_in"]["active"] is True


def test_muted_source_reports_muted_true():
    hass = _FakeHass({
        "media_player.spotify_in": _FakeState("playing", {"friendly_name": "Spotify", "volume_level": 0.4, "is_volume_muted": True}),
    })
    monitor = NexusAudioZoneMonitor(hass, ["media_player.spotify_in"])
    assert monitor.snapshot()[0]["muted"] is True


def test_no_entities_configured_returns_empty_list():
    monitor = NexusAudioZoneMonitor(_FakeHass({}), [])
    assert monitor.snapshot() == []


def test_name_falls_back_to_entity_id_when_no_friendly_name():
    hass = _FakeHass({"media_player.nameless": _FakeState("idle", {})})
    monitor = NexusAudioZoneMonitor(hass, ["media_player.nameless"])
    assert monitor.snapshot()[0]["name"] == "media_player.nameless"
