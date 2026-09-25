"""Phase C15: the Green-GO multicast group config field must reject
anything that isn't a syntactically valid IPv4 multicast address --
Green-GO's own documentation confirms this address is per-installation
(generated from the config file), so it can't be a fixed default the
way Dante/PTP's groups are, and a malformed value should be caught at
config time, not deep inside a socket join failure.
"""
from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.dmx_monitor.config_flow import _optional_multicast_group


def test_empty_string_is_accepted_as_disabled():
    assert _optional_multicast_group("") == ""
    assert _optional_multicast_group(None) == ""


def test_valid_multicast_address_is_accepted():
    assert _optional_multicast_group("239.192.5.81") == "239.192.5.81"
    assert _optional_multicast_group("224.0.1.1") == "224.0.1.1"


def test_non_multicast_address_is_rejected():
    """A perfectly valid IPv4 address that just isn't in the multicast
    range (224.0.0.0-239.255.255.255) must be rejected -- joining it as
    a 'multicast group' would silently fail to receive anything."""
    with pytest.raises(vol.Invalid):
        _optional_multicast_group("10.4.1.8")
    with pytest.raises(vol.Invalid):
        _optional_multicast_group("192.168.0.1")


def test_malformed_address_is_rejected():
    with pytest.raises(vol.Invalid):
        _optional_multicast_group("not-an-ip")
    with pytest.raises(vol.Invalid):
        _optional_multicast_group("239.192.5")
