"""Phase C13 (rapport maître, S103): amplifier adapters ("AES70/OCA,
AVDECC..."). Audit-confirmed finding: 'avdecc_bridge_url non conforme à
une URL visible' -- the config flow declared this field as a plain
`str` with zero validation, so a malformed value was only ever caught
much later, deep inside AVDECCBridgeMonitor's own poll error
(avdecc_bridge_error), not at config time. Same unvalidated-`str`
pattern also existed for CONF_RDM_BRIDGE_URL and CONF_RDMNET_BRIDGE_URL
-- fixed identically, not just the one instance the audit happened to
catch.
"""
from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.dmx_monitor.config_flow import _optional_bridge_url


def test_empty_string_is_accepted_as_disabled():
    assert _optional_bridge_url("") == ""
    assert _optional_bridge_url(None) == ""
    assert _optional_bridge_url("   ") == ""


def test_valid_http_url_is_accepted():
    assert _optional_bridge_url("http://10.4.1.50:8080/status") == "http://10.4.1.50:8080/status"


def test_valid_https_url_is_accepted():
    assert _optional_bridge_url("https://bridge.local/avdecc") == "https://bridge.local/avdecc"


def test_malformed_string_is_rejected():
    """The exact category the audit caught: a value that isn't a URL at
    all (no scheme, no structure)."""
    with pytest.raises(vol.Invalid):
        _optional_bridge_url("not-a-url")
    with pytest.raises(vol.Invalid):
        _optional_bridge_url("10.4.1.50:8080")
    with pytest.raises(vol.Invalid):
        _optional_bridge_url("10.4.1.50")


def test_non_http_scheme_is_rejected():
    """Every one of these bridges is a documented JSON-over-HTTP
    endpoint; a syntactically valid but non-http(s) URL would pass a
    bare vol.Url() check yet always fail the moment the bridge tries to
    fetch it -- caught here instead, with a clear reason."""
    with pytest.raises(vol.Invalid):
        _optional_bridge_url("ftp://10.4.1.50/status")
    with pytest.raises(vol.Invalid):
        _optional_bridge_url("mailto:admin@example.com")


def test_applied_to_all_three_bridge_url_fields():
    """The same fix was applied to CONF_AVDECC_BRIDGE_URL,
    CONF_RDM_BRIDGE_URL and CONF_RDMNET_BRIDGE_URL -- confirm the schema
    actually uses the shared validator for all three, not just the one
    the audit named."""
    import inspect
    from custom_components.dmx_monitor import config_flow

    source = inspect.getsource(config_flow._schema_for_hass)
    for field in ("CONF_AVDECC_BRIDGE_URL", "CONF_RDM_BRIDGE_URL", "CONF_RDMNET_BRIDGE_URL"):
        matching_lines = [line for line in source.splitlines() if f"const.{field}," in line]
        assert matching_lines, f"{field} not found in the schema at all"
        assert "_optional_bridge_url" in matching_lines[0], \
            f"{field}'s schema line does not use _optional_bridge_url: {matching_lines[0].strip()}"
