"""Phase C11 (rapport maître, S101): per-port IF-MIB telemetry.
async_walk() itself (snmp.py) is trusted/already exercised elsewhere;
these tests cover the column-joining and value-shaping logic in
switch_port_telemetry.py, with a fake async_walk that returns canned
per-column rows instead of touching a real socket.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor import switch_port_telemetry as spt
from custom_components.dmx_monitor import switch_temperature as temp


def _fake_walk(table: dict[str, list[tuple[str, object]]]):
    """table maps base OID -> the rows async_walk should return for it."""
    async def fake(host, community, base_oid, *, timeout=1.0, source_ip=None, max_rows=128):
        return table.get(base_oid.strip("."), [])
    return fake


def _patch_all_walks(monkeypatch, table: dict[str, list[tuple[str, object]]]):
    """SwitchPortMonitor._poll_one() now walks IF-MIB and PoE (both
    defined in switch_port_telemetry.py, sharing its async_walk binding)
    *and* ENTITY-SENSOR-MIB temperature (imported from switch_temperature.py,
    which has its own separate async_walk binding) -- tests exercising
    the full monitor need both patched, not just spt.async_walk, or the
    temperature walk falls through to a real (blocked-in-sandbox) socket
    call."""
    fake = _fake_walk(table)
    monkeypatch.setattr(spt, "async_walk", fake)
    monkeypatch.setattr(temp, "async_walk", fake)


@pytest.mark.asyncio
async def test_joins_columns_by_shared_ifindex_suffix(monkeypatch):
    table = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "GigabitEthernet1/1"), ("1.3.6.1.2.1.2.2.1.2.2", "GigabitEthernet1/2")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1), ("1.3.6.1.2.1.2.2.1.8.2", 2)],
        spt.OID_IF_SPEED: [("1.3.6.1.2.1.2.2.1.5.1", 1_000_000_000), ("1.3.6.1.2.1.2.2.1.5.2", 100_000_000)],
        spt.OID_IF_IN_ERRORS: [("1.3.6.1.2.1.2.2.1.14.1", 0), ("1.3.6.1.2.1.2.2.1.14.2", 12)],
        spt.OID_IF_OUT_ERRORS: [("1.3.6.1.2.1.2.2.1.20.1", 0), ("1.3.6.1.2.1.2.2.1.20.2", 3)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 123456), ("1.3.6.1.2.1.2.2.1.10.2", 7890)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 654321), ("1.3.6.1.2.1.2.2.1.16.2", 9870)],
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))

    ports = await spt.async_walk_if_table("10.4.1.3", "public")

    assert len(ports) == 2
    p1, p2 = ports[0], ports[1]
    assert p1 == {
        "index": "1", "name": "GigabitEthernet1/1", "oper_status": "up",
        "speed_mbps": 1000, "rx_errors": 0, "tx_errors": 0,
        "rx_octets": 123456, "tx_octets": 654321,
    }
    assert p2["name"] == "GigabitEthernet1/2"
    assert p2["oper_status"] == "down"
    assert p2["speed_mbps"] == 100
    assert p2["rx_errors"] == 12
    assert p2["tx_errors"] == 3


@pytest.mark.asyncio
async def test_ports_sorted_numerically_not_lexically(monkeypatch):
    # Lexical sort would put "10" before "2" -- must be numeric.
    table = {
        spt.OID_IF_DESCR: [
            ("1.3.6.1.2.1.2.2.1.2.2", "port2"),
            ("1.3.6.1.2.1.2.2.1.2.10", "port10"),
            ("1.3.6.1.2.1.2.2.1.2.1", "port1"),
        ],
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_if_table("10.4.1.3", "public")
    assert [p["name"] for p in ports] == ["port1", "port2", "port10"]


@pytest.mark.asyncio
async def test_missing_columns_yield_none_not_a_crash(monkeypatch):
    """A port that only answers ifDescr (e.g. a partial/slow poll) still
    produces a usable row with the missing fields as None, rather than
    being dropped or raising."""
    table = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        # every other column: no rows at all for this device
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_if_table("10.4.1.3", "public")
    assert ports == [{
        "index": "1", "name": "port1", "oper_status": "unknown",
        "speed_mbps": None, "rx_errors": None, "tx_errors": None,
        "rx_octets": None, "tx_octets": None,
    }]


@pytest.mark.asyncio
async def test_port_with_no_descr_is_dropped(monkeypatch):
    """A stray value for an index that never got a name (e.g. a device
    quirk, or a race between columns on a device with dynamically
    appearing interfaces) is not fabricated into a nameless port row."""
    table = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [
            ("1.3.6.1.2.1.2.2.1.8.1", 1),
            ("1.3.6.1.2.1.2.2.1.8.99", 1),  # index 99 never got a descr
        ],
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_if_table("10.4.1.3", "public")
    assert len(ports) == 1
    assert ports[0]["index"] == "1"


@pytest.mark.asyncio
async def test_empty_device_returns_empty_list(monkeypatch):
    monkeypatch.setattr(spt, "async_walk", _fake_walk({}))
    ports = await spt.async_walk_if_table("10.4.1.3", "public")
    assert ports == []


def test_index_suffix_helper():
    assert spt._index_suffix("1.3.6.1.2.1.2.2.1.2.7", "1.3.6.1.2.1.2.2.1.2") == "7"
    assert spt._index_suffix("1.3.6.1.2.1.2.2.1.2", "1.3.6.1.2.1.2.2.1.2") is None  # no suffix at all
    assert spt._index_suffix("1.3.6.1.2.1.2.2.1.99.7", "1.3.6.1.2.1.2.2.1.2") is None  # different column entirely


# --- SwitchPortMonitor: rate computation across successive polls -----------

@pytest.mark.asyncio
async def test_first_poll_has_no_rate_yet(monkeypatch):
    table = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 1_000_000)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 500_000)],
    }
    _patch_all_walks(monkeypatch, table)
    monitor = spt.SwitchPortMonitor({"10.4.1.3": "GigaCore"}, "public")
    await monitor.async_update()
    port = monitor.snapshot()[0]["ports"][0]
    assert port["up"] is True
    assert port["rx_mbps"] is None, "no previous sample yet -- no rate can exist"
    assert port["tx_mbps"] is None


@pytest.mark.asyncio
async def test_second_poll_computes_rate_from_octet_delta(monkeypatch):
    monitor = spt.SwitchPortMonitor({"10.4.1.3": "GigaCore"}, "public")

    table1 = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 0)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 0)],
    }
    _patch_all_walks(monkeypatch, table1)
    monkeypatch.setattr(spt, "monotonic", lambda: 1000.0)
    await monitor.async_update()

    # 10 seconds later, 12,500,000 bytes (100,000,000 bits) received --
    # exactly 10 Mbps average over the interval.
    table2 = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 12_500_000)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 0)],
    }
    _patch_all_walks(monkeypatch, table2)
    monkeypatch.setattr(spt, "monotonic", lambda: 1010.0)
    await monitor.async_update()

    port = monitor.snapshot()[0]["ports"][0]
    assert port["rx_mbps"] == 10.0
    assert port["tx_mbps"] == 0.0


@pytest.mark.asyncio
async def test_counter_reset_reports_rate_as_unavailable_not_negative(monkeypatch):
    """A device reboot resets IF-MIB counters to (near) zero -- the next
    poll's delta would be deeply negative if taken at face value. That
    must surface as 'no rate for this sample', never a negative Mbps."""
    monitor = spt.SwitchPortMonitor({"10.4.1.3": "GigaCore"}, "public")

    table1 = {
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 90_000_000)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 0)],
    }
    _patch_all_walks(monkeypatch, table1)
    monkeypatch.setattr(spt, "monotonic", lambda: 1000.0)
    await monitor.async_update()

    table2 = {  # device rebooted; counters restarted near zero
        spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        spt.OID_IF_OPER_STATUS: [("1.3.6.1.2.1.2.2.1.8.1", 1)],
        spt.OID_IF_IN_OCTETS: [("1.3.6.1.2.1.2.2.1.10.1", 100)],
        spt.OID_IF_OUT_OCTETS: [("1.3.6.1.2.1.2.2.1.16.1", 0)],
    }
    _patch_all_walks(monkeypatch, table2)
    monkeypatch.setattr(spt, "monotonic", lambda: 1010.0)
    await monitor.async_update()

    port = monitor.snapshot()[0]["ports"][0]
    assert port["rx_mbps"] is None


@pytest.mark.asyncio
async def test_unreachable_host_does_not_break_other_hosts(monkeypatch):
    async def flaky_walk(host, community, base_oid, *, timeout=1.0, source_ip=None, max_rows=128):
        if host == "10.4.1.99":
            raise OSError("unreachable")
        return {
            spt.OID_IF_DESCR: [("1.3.6.1.2.1.2.2.1.2.1", "port1")],
        }.get(base_oid.strip("."), [])

    monkeypatch.setattr(spt, "async_walk", flaky_walk)
    monkeypatch.setattr(temp, "async_walk", flaky_walk)
    monitor = spt.SwitchPortMonitor({"10.4.1.3": "GigaCore", "10.4.1.99": "Injoignable"}, "public")
    await monitor.async_update()

    names = {sw["ip"] for sw in monitor.snapshot()}
    assert names == {"10.4.1.3"}, "the unreachable host must be skipped, not crash the whole poll"


@pytest.mark.asyncio
async def test_display_name_falls_back_to_ip():
    monitor = spt.SwitchPortMonitor({}, "public")
    monitor.hosts = {}  # no hosts at all: async_update() should just no-op
    await monitor.async_update()
    assert monitor.snapshot() == []


# --- POWER-ETHERNET-MIB: per-port PoE status --------------------------

@pytest.mark.asyncio
async def test_poe_port_delivering_power(monkeypatch):
    table = {
        spt.OID_PETH_PSE_PORT_ADMIN_ENABLE: [(f"{spt.OID_PETH_PSE_PORT_ADMIN_ENABLE}.1.3", 1)],  # TruthValue true(1)
        spt.OID_PETH_PSE_PORT_DETECTION_STATUS: [(f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.1.3", 3)],  # deliveringPower(3)
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert ports == [{
        "group_index": "1", "port_index": "3",
        "admin_enabled": True, "detection_status": "delivering_power", "delivering_power": True,
    }]


@pytest.mark.asyncio
async def test_poe_port_disabled_and_admin_off(monkeypatch):
    table = {
        spt.OID_PETH_PSE_PORT_ADMIN_ENABLE: [(f"{spt.OID_PETH_PSE_PORT_ADMIN_ENABLE}.1.5", 2)],  # TruthValue false(2)
        spt.OID_PETH_PSE_PORT_DETECTION_STATUS: [(f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.1.5", 1)],  # disabled(1)
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert ports[0]["admin_enabled"] is False
    assert ports[0]["detection_status"] == "disabled"
    assert ports[0]["delivering_power"] is False


@pytest.mark.asyncio
async def test_poe_searching_status_is_not_delivering(monkeypatch):
    """searching(2) means the PSE is probing for a valid PD signature --
    not yet delivering power, must not be conflated with deliveringPower(3)."""
    table = {
        spt.OID_PETH_PSE_PORT_DETECTION_STATUS: [(f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.1.1", 2)],
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert ports[0]["detection_status"] == "searching"
    assert ports[0]["delivering_power"] is False


@pytest.mark.asyncio
async def test_poe_multiple_groups_on_a_modular_switch(monkeypatch):
    """RFC 3621's own index is (groupIndex, portIndex) precisely to
    support modular/chassis switches with more than one PSE group."""
    table = {
        spt.OID_PETH_PSE_PORT_DETECTION_STATUS: [
            (f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.1.1", 3),
            (f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.2.1", 1),
        ],
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert len(ports) == 2
    assert [(p["group_index"], p["port_index"]) for p in ports] == [("1", "1"), ("2", "1")]


@pytest.mark.asyncio
async def test_poe_port_without_detection_status_is_dropped(monkeypatch):
    table = {
        spt.OID_PETH_PSE_PORT_ADMIN_ENABLE: [(f"{spt.OID_PETH_PSE_PORT_ADMIN_ENABLE}.1.9", 1)],
        # no detection status answered for this index at all
    }
    monkeypatch.setattr(spt, "async_walk", _fake_walk(table))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert ports == []


@pytest.mark.asyncio
async def test_poe_no_data_returns_empty_list(monkeypatch):
    monkeypatch.setattr(spt, "async_walk", _fake_walk({}))
    ports = await spt.async_walk_poe_ports("10.4.1.3", "public")
    assert ports == []


def test_peth_port_key_requires_exactly_two_parts():
    base = spt.OID_PETH_PSE_PORT_DETECTION_STATUS
    assert spt._peth_port_key(f"{base}.1.3", base) == ("1", "3")
    assert spt._peth_port_key(f"{base}.1.3.1", base) is None, "three parts -- that's an LLDP-shaped index, not this table's"
    assert spt._peth_port_key(base, base) is None


@pytest.mark.asyncio
async def test_switch_port_monitor_includes_poe_ports_per_switch(monkeypatch):
    table = {
        spt.OID_IF_DESCR: [(f"{spt.OID_IF_DESCR}.1", "port1")],
        spt.OID_IF_OPER_STATUS: [(f"{spt.OID_IF_OPER_STATUS}.1", 1)],
        spt.OID_PETH_PSE_PORT_DETECTION_STATUS: [(f"{spt.OID_PETH_PSE_PORT_DETECTION_STATUS}.1.1", 3)],
    }
    _patch_all_walks(monkeypatch, table)
    monitor = spt.SwitchPortMonitor({"10.4.1.3": "GigaCore"}, "public")
    await monitor.async_update()
    switch = monitor.snapshot()[0]
    assert switch["poe_ports"] == [{
        "group_index": "1", "port_index": "1",
        "admin_enabled": None, "detection_status": "delivering_power", "delivering_power": True,
    }]
    # And the IF-MIB ports list is unaffected by adding PoE alongside it.
    assert switch["ports"][0]["name"] == "port1"
