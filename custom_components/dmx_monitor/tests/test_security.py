"""Tests for custom_components/dmx_monitor/security.py.

No Home Assistant fixtures needed -- security.py has no HA dependency of
its own. Only importing it goes through custom_components/dmx_monitor's
package __init__, which does depend on Home Assistant being installed
(pip install pytest-homeassistant-custom-component pulls that in).
"""
from __future__ import annotations

import tempfile
import time

import pytest

from custom_components.dmx_monitor.security import (
    SecurityManager,
    ip_allowed,
    normalize_ip_allowlist,
    redact,
    validate_archive_limits,
)


def test_unconfigured_manager_requires_password_setup_first():
    with tempfile.TemporaryDirectory() as tmp:
        manager = SecurityManager(tmp, autoload=False)
        assert manager.state.configured is False
        with pytest.raises(PermissionError, match="configure a Show Network password"):
            manager.require_unlocked()


def test_set_password_then_unlock_and_lock():
    with tempfile.TemporaryDirectory() as tmp:
        manager = SecurityManager(tmp, autoload=False)
        manager.set_password("correct-horse-battery-staple")
        assert manager.state.configured is True
        assert manager.state.unlocked is False  # setting a password does not itself unlock

        manager.unlock("correct-horse-battery-staple")
        assert manager.state.unlocked is True
        manager.require_unlocked()  # must not raise

        manager.lock()
        assert manager.state.unlocked is False
        with pytest.raises(PermissionError):
            manager.require_unlocked()


def test_unlock_with_wrong_password_raises_and_does_not_unlock():
    with tempfile.TemporaryDirectory() as tmp:
        manager = SecurityManager(tmp, autoload=False)
        manager.set_password("correct-horse-battery-staple")
        with pytest.raises(PermissionError):
            manager.unlock("wrong-password")
        assert manager.state.unlocked is False


def test_password_must_be_at_least_8_characters():
    with tempfile.TemporaryDirectory() as tmp:
        manager = SecurityManager(tmp, autoload=False)
        with pytest.raises(ValueError):
            manager.set_password("short")


def test_brute_force_lockout_after_five_failed_attempts():
    with tempfile.TemporaryDirectory() as tmp:
        manager = SecurityManager(tmp, autoload=False)
        manager.set_password("correct-horse-battery-staple")
        for _ in range(5):
            assert manager.verify("wrong") is False
        # Even the CORRECT password is rejected while the 30s lockout is active.
        assert manager.verify("correct-horse-battery-staple") is False


def test_restart_does_not_auto_unlock_even_with_autoload():
    """A Home Assistant restart must never resume an unlocked state."""
    with tempfile.TemporaryDirectory() as tmp:
        first = SecurityManager(tmp, autoload=False)
        first.set_password("correct-horse-battery-staple")
        first.unlock("correct-horse-battery-staple")
        assert first.state.unlocked is True

        # Simulate a restart: a brand-new instance pointed at the same
        # config directory. The password itself is loaded back (autoload),
        # but the unlocked state is never persisted or resumed.
        second = SecurityManager(tmp, autoload=True)
        assert second.state.configured is True  # password survives
        assert second.state.unlocked is False  # unlock state never does


def test_ip_allowlist_empty_allows_everything():
    assert ip_allowed("8.8.8.8", None) is True
    assert ip_allowed("10.0.0.1", ()) is True


def test_ip_allowlist_restricts_to_configured_networks():
    allowlist = normalize_ip_allowlist(["10.0.0.0/24", "192.168.1.5"])
    assert ip_allowed("10.0.0.42", allowlist) is True
    assert ip_allowed("192.168.1.5", allowlist) is True
    assert ip_allowed("8.8.8.8", allowlist) is False


def test_ip_allowlist_raises_on_invalid_entry():
    with pytest.raises(ValueError):
        normalize_ip_allowlist(["not-an-ip-or-cidr"])


def test_redact_masks_sensitive_keys_but_not_ordinary_ids():
    data = {
        "community": "public",
        "password": "hunter2",
        "sysName": "switch1",
        "nested": {"api_key": "abc123", "ok": 1},
        "key": "amp-42",  # a plain record identifier, must survive untouched
    }
    out = redact(data)
    assert out["community"] != "public"
    assert out["password"] != "hunter2"
    assert out["nested"]["api_key"] != "abc123"
    assert out["sysName"] == "switch1"
    assert out["nested"]["ok"] == 1
    assert out["key"] == "amp-42"


def test_validate_archive_limits_clamps_out_of_range_values():
    days, size = validate_archive_limits(999999, 1)
    assert 1 <= days <= 3650
    assert 64 * 1024 <= size <= 100 * 1024 * 1024


def test_validate_archive_limits_passes_through_valid_values():
    days, size = validate_archive_limits(7, 5 * 1024 * 1024)
    assert days == 7
    assert size == 5 * 1024 * 1024
