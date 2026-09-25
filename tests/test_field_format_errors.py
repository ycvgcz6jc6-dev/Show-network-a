"""_field_format_errors coverage for the two fields that never had a
dedicated pre-existing test file: millumin_ping_target and pdu_hosts.
Same audit fix as test_bridge_url_validation_c13.py /
test_greengo_multicast_validation_c15.py -- validation checked after
form submission, never as a vol.All(str, <function>) schema validator
(which crashed the whole config/options flow with a 500 error).
"""
from __future__ import annotations

from custom_components.dmx_monitor.config_flow import _field_format_errors
from custom_components.dmx_monitor import const


def test_millumin_ping_target_empty_is_accepted():
    assert _field_format_errors({const.CONF_MILLUMIN_PING_TARGET: ""}) == {}


def test_millumin_ping_target_valid_host_port_is_accepted():
    assert _field_format_errors({const.CONF_MILLUMIN_PING_TARGET: "10.4.1.20:7001"}) == {}


def test_millumin_ping_target_missing_colon_is_rejected():
    errors = _field_format_errors({const.CONF_MILLUMIN_PING_TARGET: "10.4.1.20"})
    assert errors == {const.CONF_MILLUMIN_PING_TARGET: "invalid_host_port"}


def test_millumin_ping_target_non_numeric_port_is_rejected():
    errors = _field_format_errors({const.CONF_MILLUMIN_PING_TARGET: "10.4.1.20:abc"})
    assert errors == {const.CONF_MILLUMIN_PING_TARGET: "invalid_host_port"}


def test_millumin_ping_target_out_of_range_port_is_rejected():
    errors = _field_format_errors({const.CONF_MILLUMIN_PING_TARGET: "10.4.1.20:99999"})
    assert errors == {const.CONF_MILLUMIN_PING_TARGET: "invalid_host_port"}


def test_pdu_hosts_empty_is_accepted():
    assert _field_format_errors({const.CONF_PDU_HOSTS: ""}) == {}


def test_pdu_hosts_valid_single_entry_is_accepted():
    assert _field_format_errors({const.CONF_PDU_HOSTS: "10.4.1.9:apc"}) == {}


def test_pdu_hosts_valid_multiple_entries_is_accepted():
    assert _field_format_errors({const.CONF_PDU_HOSTS: "10.4.1.9:apc,10.4.1.10:raritan"}) == {}


def test_pdu_hosts_missing_vendor_is_rejected():
    errors = _field_format_errors({const.CONF_PDU_HOSTS: "10.4.1.9"})
    assert errors == {const.CONF_PDU_HOSTS: "invalid_pdu_hosts"}


def test_pdu_hosts_unsupported_vendor_is_rejected():
    errors = _field_format_errors({const.CONF_PDU_HOSTS: "10.4.1.9:eaton"})
    assert errors == {const.CONF_PDU_HOSTS: "invalid_pdu_hosts"}


def test_pdu_hosts_one_bad_entry_among_good_ones_is_still_rejected():
    errors = _field_format_errors({const.CONF_PDU_HOSTS: "10.4.1.9:apc,10.4.1.99:bogus"})
    assert errors == {const.CONF_PDU_HOSTS: "invalid_pdu_hosts"}


def test_multiple_fields_can_error_at_once():
    """Confirms errors from different fields don't clobber each other in
    the merged dict returned to async_show_form."""
    errors = _field_format_errors({
        const.CONF_PDU_HOSTS: "bad",
        const.CONF_MILLUMIN_PING_TARGET: "also-bad",
        const.CONF_GREENGO_MULTICAST_GROUP: "10.0.0.1",  # not multicast
    })
    assert set(errors.keys()) == {
        const.CONF_PDU_HOSTS, const.CONF_MILLUMIN_PING_TARGET, const.CONF_GREENGO_MULTICAST_GROUP,
    }
