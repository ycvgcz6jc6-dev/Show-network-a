"""Tests for custom_components/dmx_monitor/services/common.py.

Covers the P1 audit fix: services must never silently guess which config
entry to act on when more than one Show Network entry is configured.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor.services.common import coordinator_for_call


class _Call:
    def __init__(self, data):
        self.data = data


class _Hass:
    def __init__(self, entries):
        self.data = {"dmx_monitor": entries}


def test_single_entry_auto_resolves_without_entry_id():
    hass = _Hass({"entry1": {"coordinator": "COORD_1"}})
    assert coordinator_for_call(hass, _Call({})) == "COORD_1"


def test_multiple_entries_without_entry_id_raises():
    hass = _Hass({"entry1": {"coordinator": "COORD_1"}, "entry2": {"coordinator": "COORD_2"}})
    with pytest.raises(ValueError, match="entry_id is required"):
        coordinator_for_call(hass, _Call({}))


def test_multiple_entries_with_entry_id_resolves_correctly():
    hass = _Hass({"entry1": {"coordinator": "COORD_1"}, "entry2": {"coordinator": "COORD_2"}})
    assert coordinator_for_call(hass, _Call({"entry_id": "entry2"})) == "COORD_2"


def test_unknown_entry_id_raises():
    hass = _Hass({"entry1": {"coordinator": "COORD_1"}})
    with pytest.raises(ValueError, match="Unknown config entry"):
        coordinator_for_call(hass, _Call({"entry_id": "does-not-exist"}))
