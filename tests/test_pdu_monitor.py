"""Tests for pdu_monitor.py. OIDs and value mappings verified against
Network UPS Tools' own open-source driver source
(apc-pdu-mib.c, raritan-px2-mib.c) -- test fixtures below use exactly
those confirmed OIDs and enum values, not invented ones.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor import pdu_monitor as pdu



def _fake_get(values: dict[str, object]):
    async def fake(host, community, oid, timeout=1.5, source_ip=None):
        return values.get(oid.strip("."))
    return fake


def _fake_walk(table: dict[str, list[tuple[str, object]]]):
    async def fake(host, community, base_oid, *, timeout=1.0, source_ip=None, max_rows=128):
        return table.get(base_oid.strip("."), [])
    return fake


# --- APC ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_apc_online_reports_model_serial_and_outlets(monkeypatch):
    get_values = {
        pdu.APC_OID_MODEL: "AP7920", pdu.APC_OID_SERIAL: "5A1234E00874",
        pdu.APC_OID_FIRMWARE: "v3.7.3",
    }
    walk_table = {
        pdu.APC_OID_OUTLET_DESC: [(f"{pdu.APC_OID_OUTLET_DESC}.1", "Console"), (f"{pdu.APC_OID_OUTLET_DESC}.2", "Amp")],
        pdu.APC_OID_OUTLET_STATUS: [(f"{pdu.APC_OID_OUTLET_STATUS}.1", 1), (f"{pdu.APC_OID_OUTLET_STATUS}.2", 2)],
    }
    monkeypatch.setattr(pdu, "async_get", _fake_get(get_values))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk(walk_table))

    monitor = pdu.PDUMonitor({"10.4.1.9": "apc"})
    await monitor.async_update()
    row = monitor.snapshot()[0]
    assert row["online"] is True
    assert row["model"] == "AP7920"
    assert row["serial"] == "5A1234E00874"
    assert row["outlet_count"] == 2
    assert row["outlets_on"] == 1
    outlets = {o["index"]: o for o in row["outlets"]}
    assert outlets["1"] == {"index": "1", "name": "Console", "state": "on"}
    assert outlets["2"] == {"index": "2", "name": "Amp", "state": "off"}
    assert row["scope"] == "status_only_no_outlet_control"


@pytest.mark.asyncio
async def test_apc_unreachable_reports_offline(monkeypatch):
    monkeypatch.setattr(pdu, "async_get", _fake_get({}))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk({}))
    monitor = pdu.PDUMonitor({"10.4.1.9": "apc"})
    await monitor.async_update()
    row = monitor.snapshot()[0]
    assert row["online"] is False
    assert row["error"] is not None


# --- Raritan -------------------------------------------------------------

@pytest.mark.asyncio
async def test_raritan_online_reports_model_and_outlets(monkeypatch):
    get_values = {
        pdu.RARITAN_OID_MODEL: "PX2-5475", pdu.RARITAN_OID_SERIAL: "PEG1234567",
    }
    walk_table = {
        pdu.RARITAN_OID_OUTLET_DESC: [(f"{pdu.RARITAN_OID_OUTLET_DESC}.1", "Rack A")],
        pdu.RARITAN_OID_OUTLET_STATUS: [(f"{pdu.RARITAN_OID_OUTLET_STATUS}.1", 7)],  # on(7)
    }
    monkeypatch.setattr(pdu, "async_get", _fake_get(get_values))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk(walk_table))

    monitor = pdu.PDUMonitor({"10.4.1.10": "raritan"})
    await monitor.async_update()
    row = monitor.snapshot()[0]
    assert row["online"] is True
    assert row["model"] == "PX2-5475"
    assert row["outlets"][0]["state"] == "on"


@pytest.mark.asyncio
async def test_raritan_off_state_value_8(monkeypatch):
    """Confirms 8 (not e.g. 0 or 2) is the verified 'off' value for
    Raritan's shared sensor-state enum -- distinct from APC's own
    2=off mapping, a real difference between the two vendors."""
    get_values = {pdu.RARITAN_OID_MODEL: "PX2-5475"}
    walk_table = {
        pdu.RARITAN_OID_OUTLET_STATUS: [(f"{pdu.RARITAN_OID_OUTLET_STATUS}.1", 8)],
    }
    monkeypatch.setattr(pdu, "async_get", _fake_get(get_values))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk(walk_table))
    monitor = pdu.PDUMonitor({"10.4.1.10": "raritan"})
    await monitor.async_update()
    assert monitor.snapshot()[0]["outlets"][0]["state"] == "off"


# --- Mixed fleet / vendor selection ----------------------------------------

@pytest.mark.asyncio
async def test_mixed_apc_and_raritan_hosts_polled_independently(monkeypatch):
    get_values = {
        pdu.APC_OID_MODEL: "AP7920",
        pdu.RARITAN_OID_MODEL: "PX2-5475",
    }
    monkeypatch.setattr(pdu, "async_get", _fake_get(get_values))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk({}))

    monitor = pdu.PDUMonitor({"10.4.1.9": "apc", "10.4.1.10": "raritan"})
    await monitor.async_update()
    by_host = {r["host"]: r for r in monitor.snapshot()}
    assert by_host["10.4.1.9"]["vendor"] == "apc"
    assert by_host["10.4.1.9"]["model"] == "AP7920"
    assert by_host["10.4.1.10"]["vendor"] == "raritan"
    assert by_host["10.4.1.10"]["model"] == "PX2-5475"


def test_unsupported_vendor_is_silently_excluded():
    """No auto-detection, no guessing -- a host with an unrecognized
    vendor string is not polled at all rather than assumed to be one
    of the two known vendors."""
    monitor = pdu.PDUMonitor({"10.4.1.9": "eaton"})  # not yet supported
    assert monitor.hosts == {}


@pytest.mark.asyncio
async def test_no_hosts_is_a_noop():
    monitor = pdu.PDUMonitor({})
    await monitor.async_update()
    assert monitor.snapshot() == []


@pytest.mark.asyncio
async def test_unknown_status_value_reported_as_unknown_not_guessed(monkeypatch):
    """A status value outside the verified {1,2} (APC) or {7,8}
    (Raritan) mapping must never be silently interpreted as on/off."""
    get_values = {pdu.APC_OID_MODEL: "AP7920"}
    walk_table = {
        pdu.APC_OID_OUTLET_STATUS: [(f"{pdu.APC_OID_OUTLET_STATUS}.1", 99)],
    }
    monkeypatch.setattr(pdu, "async_get", _fake_get(get_values))
    monkeypatch.setattr(pdu, "async_walk", _fake_walk(walk_table))
    monitor = pdu.PDUMonitor({"10.4.1.9": "apc"})
    await monitor.async_update()
    assert monitor.snapshot()[0]["outlets"][0]["state"] == "unknown"
