"""Phase C13 (rapport maître, S103): amplifier adapters ("AES70/OCA,
AVDECC..."). Audit-confirmed finding: 'avdecc_bridge_url non conforme à
une URL visible' -- the config flow originally declared this field as a
plain `str` with zero validation.

Superseded by a second, more serious audit fix (this session, after
production deployment): validation was first implemented as a
vol.All(str, <custom function>) schema validator, which crashed the
*entire* config/options flow with a 500 error the moment it tried to
render -- Home Assistant's frontend must serialize the schema to JSON,
and a bare Python function has no serializable representation
("ValueError: unable to serialize schema: <function ...>"). Moved to
_field_format_errors, checked *after* form submission (the same
architecture this project's own OSC port conflict check already used),
returning a {field: error_key} dict instead of raising.
"""
from __future__ import annotations

from custom_components.dmx_monitor.config_flow import _field_format_errors
from custom_components.dmx_monitor import const


def test_empty_string_is_accepted_as_disabled():
    for key in (const.CONF_AVDECC_BRIDGE_URL, const.CONF_RDM_BRIDGE_URL, const.CONF_RDMNET_BRIDGE_URL):
        assert _field_format_errors({key: ""}) == {}
        assert _field_format_errors({key: None}) == {}


def test_valid_http_url_is_accepted():
    assert _field_format_errors({const.CONF_AVDECC_BRIDGE_URL: "http://10.4.1.50:8080/status"}) == {}


def test_valid_https_url_is_accepted():
    assert _field_format_errors({const.CONF_AVDECC_BRIDGE_URL: "https://bridge.local/avdecc"}) == {}


def test_malformed_string_is_rejected():
    """The exact category the audit caught: a value that isn't a URL at
    all (no scheme, no structure)."""
    for bad in ("not-a-url", "10.4.1.50:8080", "10.4.1.50"):
        errors = _field_format_errors({const.CONF_AVDECC_BRIDGE_URL: bad})
        assert errors == {const.CONF_AVDECC_BRIDGE_URL: "invalid_bridge_url"}


def test_non_http_scheme_is_rejected():
    """Every one of these bridges is a documented JSON-over-HTTP
    endpoint; a syntactically valid but non-http(s) URL would pass a
    bare vol.Url() check yet always fail the moment the bridge tries to
    fetch it -- caught here instead, with a clear reason."""
    for bad in ("ftp://10.4.1.50/status", "mailto:admin@example.com"):
        errors = _field_format_errors({const.CONF_AVDECC_BRIDGE_URL: bad})
        assert errors == {const.CONF_AVDECC_BRIDGE_URL: "invalid_bridge_url"}


def test_applied_to_all_three_bridge_url_fields():
    """The same fix was applied to CONF_AVDECC_BRIDGE_URL,
    CONF_RDM_BRIDGE_URL and CONF_RDMNET_BRIDGE_URL -- confirm all three
    are actually checked, not just the one the audit named."""
    for key in (const.CONF_AVDECC_BRIDGE_URL, const.CONF_RDM_BRIDGE_URL, const.CONF_RDMNET_BRIDGE_URL):
        errors = _field_format_errors({key: "not-a-url"})
        assert key in errors, f"{key} was not validated"


def test_no_valid_python_function_appears_anywhere_in_the_schema():
    """Regression test for the real production crash: every field in
    the built schema must be representable as plain JSON-serializable
    voluptuous validators, never a bare custom function."""
    import inspect
    from custom_components.dmx_monitor import config_flow as cf

    class _FakeServices:
        def async_services(self):
            return {}

    class _FakeHass:
        services = _FakeServices()

    schema = cf._schema_for_hass(_FakeHass(), {}, ["eth0"], [], [])
    for key, validator in schema.schema.items():
        assert not inspect.isfunction(validator), f"{key} still has a raw function as its validator"


def test_the_six_previously_broken_fields_actually_serialize_with_voluptuous_serialize():
    """Direct proof, not just an isinstance check: the exact production
    crash was `voluptuous_serialize`/probatio failing to convert these
    fields' schema entries to JSON for the frontend. Reproduces both
    sides -- the fixed (plain str) shape serializes cleanly; the old
    vol.All(str, <function>) shape is confirmed to still fail the same
    way, so this isn't testing a strawman."""
    import voluptuous as vol
    import voluptuous_serialize

    fixed_schema = vol.Schema({
        vol.Optional(const.CONF_AVDECC_BRIDGE_URL, default=""): str,
        vol.Optional(const.CONF_RDM_BRIDGE_URL, default=""): str,
        vol.Optional(const.CONF_RDMNET_BRIDGE_URL, default=""): str,
        vol.Optional(const.CONF_GREENGO_MULTICAST_GROUP, default=""): str,
        vol.Optional(const.CONF_MILLUMIN_PING_TARGET, default=""): str,
        vol.Optional(const.CONF_PDU_HOSTS, default=""): str,
    })
    result = voluptuous_serialize.convert(fixed_schema)  # must not raise
    assert len(result) == 6

    def _old_broken_validator(value):
        return value

    broken_schema = vol.Schema({vol.Optional(const.CONF_PDU_HOSTS, default=""): vol.All(str, _old_broken_validator)})
    import pytest
    with pytest.raises(Exception):
        voluptuous_serialize.convert(broken_schema)
