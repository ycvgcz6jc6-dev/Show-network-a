"""Phase C15: the Green-GO multicast group config field must reject
anything that isn't a syntactically valid IPv4 multicast address --
Green-GO's own documentation confirms this address is per-installation
(generated from the config file), so it can't be a fixed default the
way Dante/PTP's groups are, and a malformed value should be caught at
config time, not deep inside a socket join failure.

Superseded by a later audit fix (this session, after production
deployment): validation was first a vol.All(str, <custom function>)
schema validator, which crashed the whole config/options flow with a
500 error the instant Home Assistant's frontend tried to serialize the
schema to JSON (a bare function has no serializable form). Moved to
_field_format_errors, checked after form submission -- see
test_bridge_url_validation_c13.py for the fuller explanation, shared by
both fixes.
"""
from __future__ import annotations

from custom_components.dmx_monitor.config_flow import _field_format_errors
from custom_components.dmx_monitor import const


def test_empty_string_is_accepted_as_disabled():
    assert _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: ""}) == {}
    assert _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: None}) == {}


def test_valid_multicast_address_is_accepted():
    assert _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: "239.192.5.81"}) == {}
    assert _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: "224.0.1.1"}) == {}


def test_non_multicast_address_is_rejected():
    """A perfectly valid IPv4 address that just isn't in the multicast
    range (224.0.0.0-239.255.255.255) must be rejected -- joining it as
    a 'multicast group' would silently fail to receive anything."""
    for bad in ("10.4.1.8", "192.168.0.1"):
        errors = _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: bad})
        assert errors == {const.CONF_GREENGO_MULTICAST_GROUP: "invalid_multicast_group"}


def test_malformed_address_is_rejected():
    for bad in ("not-an-ip", "239.192.5"):
        errors = _field_format_errors({const.CONF_GREENGO_MULTICAST_GROUP: bad})
        assert errors == {const.CONF_GREENGO_MULTICAST_GROUP: "invalid_multicast_group"}
