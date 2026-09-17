"""Tests for the SSRF fix in ma3_web_remote_view.py (audit Z-03).

An earlier version of this proxy took `station_ip` straight from the
request URL with no validation, letting an authenticated Home Assistant
user make Home Assistant issue outbound requests to an arbitrary host
(including internal/cloud-metadata addresses). These tests confirm the fix:
only an IP already present in the entry's own passively-observed MA-Net3
station inventory is ever proxied to.
"""
from __future__ import annotations

from custom_components.dmx_monitor.ma3_web_remote_view import (
    _is_known_station,
    _resolve_entry_and_coordinator,
)


class _FakeMARemote:
    def __init__(self, stations):
        self.stations = stations


class _FakeCoordinator:
    def __init__(self, station_ips):
        self.ma_remote = _FakeMARemote({ip: object() for ip in station_ips})


class _FakeHass:
    def __init__(self, entries):
        self.data = {"dmx_monitor": entries}


def test_known_station_ip_is_allowed():
    coordinator = _FakeCoordinator(["10.2.1.1", "10.2.1.2"])
    assert _is_known_station(coordinator, "10.2.1.1") is True


def test_never_observed_ip_is_rejected_even_if_syntactically_valid():
    coordinator = _FakeCoordinator(["10.2.1.1"])
    assert _is_known_station(coordinator, "10.2.1.99") is False


def test_ssrf_attempt_against_cloud_metadata_endpoint_is_rejected():
    coordinator = _FakeCoordinator(["10.2.1.1"])
    assert _is_known_station(coordinator, "169.254.169.254") is False


def test_hostname_instead_of_ip_is_rejected_outright():
    coordinator = _FakeCoordinator(["10.2.1.1"])
    assert _is_known_station(coordinator, "internal-admin.local") is False


def test_single_entry_auto_resolves():
    coordinator = _FakeCoordinator(["10.2.1.1"])
    hass = _FakeHass({"entry1": {"coordinator": coordinator}})
    entry_id, resolved = _resolve_entry_and_coordinator(hass, "")
    assert entry_id == "entry1"
    assert resolved is coordinator


def test_multiple_entries_without_entry_id_refuses_to_guess():
    coord_a = _FakeCoordinator(["10.2.1.1"])
    coord_b = _FakeCoordinator(["10.2.1.2"])
    hass = _FakeHass({"entry1": {"coordinator": coord_a}, "entry2": {"coordinator": coord_b}})
    entry_id, resolved = _resolve_entry_and_coordinator(hass, "")
    assert resolved is None


def test_multiple_entries_with_explicit_entry_id_resolves_correctly():
    coord_a = _FakeCoordinator(["10.2.1.1"])
    coord_b = _FakeCoordinator(["10.2.1.2"])
    hass = _FakeHass({"entry1": {"coordinator": coord_a}, "entry2": {"coordinator": coord_b}})
    entry_id, resolved = _resolve_entry_and_coordinator(hass, "entry2")
    assert entry_id == "entry2"
    assert resolved is coord_b
