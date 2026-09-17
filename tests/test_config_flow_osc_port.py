"""Tests for the OSC port pre-flight check in config_flow.py.

Covers the P1 audit fix: a UDP port conflict should be caught at
configuration time with a clear field-level error, not just discovered
later in the Home Assistant log after the integration fails to start.
"""
from __future__ import annotations

import socket

import pytest

from custom_components.dmx_monitor import const
from custom_components.dmx_monitor.config_flow import (
    _choices_for_hass,
    _osc_port_conflict_error,
    _udp_port_available,
)


class _FakeHass:
    async def async_add_executor_job(self, fn, *args):
        return fn(*args)


@pytest.mark.asyncio
async def test_choices_for_hass_discovers_choices_in_executor(monkeypatch):
    class _Port:
        device = "/dev/ttyUSB0"

    monkeypatch.setattr(
        "custom_components.dmx_monitor.config_flow.network_interface_snapshot",
        lambda: [{"addresses": ["192.0.2.10", "fe80::1"]}],
    )
    monkeypatch.setattr(
        "custom_components.dmx_monitor.config_flow.discover_ports",
        lambda: [_Port()],
    )
    monkeypatch.setattr(
        "custom_components.dmx_monitor.config_flow.MIDIInputRuntime.list_input_ports",
        lambda: ["MIDI In"],
    )

    assert await _choices_for_hass(_FakeHass()) == (
        ["0.0.0.0", "192.0.2.10"],
        ["/dev/ttyUSB0"],
        ["MIDI In"],
    )


def test_udp_port_available_detects_a_free_port():
    assert _udp_port_available("0.0.0.0", 0) is True  # port 0 = "let the OS pick a free one"


def test_udp_port_available_detects_a_genuinely_taken_port():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("0.0.0.0", 0))
    taken_port = blocker.getsockname()[1]
    try:
        assert _udp_port_available("0.0.0.0", taken_port) is False
    finally:
        blocker.close()


@pytest.mark.asyncio
async def test_conflict_error_flags_a_taken_port_when_osc_enabled():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("0.0.0.0", 0))
    taken_port = blocker.getsockname()[1]
    try:
        hass = _FakeHass()
        errors = await _osc_port_conflict_error(hass, {
            const.CONF_OSC_INPUT_ENABLED: True,
            const.CONF_OSC_INPUT_PORT: taken_port,
        })
        assert errors == {"osc_input_port": "port_in_use"}
    finally:
        blocker.close()


@pytest.mark.asyncio
async def test_conflict_error_skipped_when_osc_disabled():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("0.0.0.0", 0))
    taken_port = blocker.getsockname()[1]
    try:
        hass = _FakeHass()
        errors = await _osc_port_conflict_error(hass, {
            const.CONF_OSC_INPUT_ENABLED: False,
            const.CONF_OSC_INPUT_PORT: taken_port,
        })
        assert errors == {}
    finally:
        blocker.close()


@pytest.mark.asyncio
async def test_re_saving_the_same_port_the_entry_already_owns_is_not_a_false_positive():
    """The running entry's own listener legitimately holds its configured
    port -- re-saving unchanged options must never conflict against itself."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("0.0.0.0", 0))
    taken_port = blocker.getsockname()[1]
    try:
        hass = _FakeHass()
        errors = await _osc_port_conflict_error(
            hass,
            {const.CONF_OSC_INPUT_ENABLED: True, const.CONF_OSC_INPUT_PORT: taken_port},
            previous_port=taken_port,
        )
        assert errors == {}
    finally:
        blocker.close()


@pytest.mark.asyncio
async def test_changing_to_a_different_taken_port_still_flags_a_real_conflict():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("0.0.0.0", 0))
    taken_port = blocker.getsockname()[1]
    try:
        hass = _FakeHass()
        errors = await _osc_port_conflict_error(
            hass,
            {const.CONF_OSC_INPUT_ENABLED: True, const.CONF_OSC_INPUT_PORT: taken_port},
            previous_port=taken_port + 1,  # entry previously used a different port
        )
        assert errors == {"osc_input_port": "port_in_use"}
    finally:
        blocker.close()
