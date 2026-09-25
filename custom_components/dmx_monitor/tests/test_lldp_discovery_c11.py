"""Phase C11 (rapport maître, S101): LLDP neighbor discovery via the
standard LLDP-MIB. async_walk() itself (snmp.py) is trusted/already
exercised elsewhere; these tests cover the composite-index parsing and
column-joining logic in lldp_discovery.py, with a fake async_walk
returning canned rows using LLDP-MIB's real (timeMark.localPortNum.
remIndex) three-part index shape.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor import lldp_discovery as lldp



def _fake_walk(table: dict[str, list[tuple[str, object]]]):
    async def fake(host, community, base_oid, *, timeout=1.0, source_ip=None, max_rows=128):
        return table.get(base_oid.strip("."), [])
    return fake


@pytest.mark.asyncio
async def test_single_neighbor_on_one_local_port(monkeypatch):
    # Real LLDP-MIB shape: <column base>.<timeMark>.<localPortNum>.<remIndex>
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID_SUBTYPE: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID_SUBTYPE}.12.3.1", 4)],  # 4 = mac_address
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.12.3.1", "aa:bb:cc:dd:ee:ff")],
        lldp.OID_LLDP_REM_PORT_ID_SUBTYPE: [(f"{lldp.OID_LLDP_REM_PORT_ID_SUBTYPE}.12.3.1", 5)],  # 5 = interface_name
        lldp.OID_LLDP_REM_PORT_ID: [(f"{lldp.OID_LLDP_REM_PORT_ID}.12.3.1", "GigabitEthernet0/24")],
        lldp.OID_LLDP_REM_PORT_DESC: [(f"{lldp.OID_LLDP_REM_PORT_DESC}.12.3.1", "Uplink to core")],
        lldp.OID_LLDP_REM_SYS_NAME: [(f"{lldp.OID_LLDP_REM_SYS_NAME}.12.3.1", "core-switch-01")],
        lldp.OID_LLDP_REM_SYS_DESC: [(f"{lldp.OID_LLDP_REM_SYS_DESC}.12.3.1", "Cisco IOS Software")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))

    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")

    assert len(neighbors) == 1
    n = neighbors[0]
    assert n["local_port_num"] == "3"
    assert n["remote_index"] == "1"
    assert n["chassis_id"] == "aa:bb:cc:dd:ee:ff"
    assert n["chassis_id_type"] == "mac_address"
    assert n["port_id"] == "GigabitEthernet0/24"
    assert n["port_id_type"] == "interface_name"
    assert n["port_desc"] == "Uplink to core"
    assert n["sys_name"] == "core-switch-01"
    assert n["sys_desc"] == "Cisco IOS Software"


@pytest.mark.asyncio
async def test_local_port_name_resolved_from_local_port_table(monkeypatch):
    table = {
        lldp.OID_LLDP_LOC_PORT_ID: [(f"{lldp.OID_LLDP_LOC_PORT_ID}.3", "Gi0/3")],
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:bb:cc:dd:ee:ff")],
        lldp.OID_LLDP_REM_PORT_ID: [(f"{lldp.OID_LLDP_REM_PORT_ID}.1.3.1", "eth0")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors[0]["local_port_name"] == "Gi0/3"


@pytest.mark.asyncio
async def test_local_port_desc_used_when_id_missing(monkeypatch):
    table = {
        lldp.OID_LLDP_LOC_PORT_DESC: [(f"{lldp.OID_LLDP_LOC_PORT_DESC}.3", "Port 3 description")],
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:bb:cc:dd:ee:ff")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors[0]["local_port_name"] == "Port 3 description"


@pytest.mark.asyncio
async def test_local_port_name_absent_is_none_not_a_crash(monkeypatch):
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.7.1", "aa:bb:cc:dd:ee:ff")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors[0]["local_port_name"] is None


@pytest.mark.asyncio
async def test_two_neighbors_on_two_different_local_ports(monkeypatch):
    table = {
        lldp.OID_LLDP_REM_SYS_NAME: [
            (f"{lldp.OID_LLDP_REM_SYS_NAME}.1.1.1", "switch-a"),
            (f"{lldp.OID_LLDP_REM_SYS_NAME}.1.2.1", "switch-b"),
        ],
        lldp.OID_LLDP_REM_CHASSIS_ID: [
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.1.1", "aa:aa:aa:aa:aa:aa"),
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.2.1", "bb:bb:bb:bb:bb:bb"),
        ],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert len(neighbors) == 2
    assert [n["sys_name"] for n in neighbors] == ["switch-a", "switch-b"], "must sort by local_port_num"


@pytest.mark.asyncio
async def test_two_neighbors_on_same_port_through_unmanaged_hub(monkeypatch):
    """lldpRemIndex exists precisely for this: more than one neighbor can
    be seen on a single local port if it's connected through a hub or
    unmanaged switch."""
    table = {
        lldp.OID_LLDP_REM_SYS_NAME: [
            (f"{lldp.OID_LLDP_REM_SYS_NAME}.1.4.1", "device-1"),
            (f"{lldp.OID_LLDP_REM_SYS_NAME}.1.4.2", "device-2"),
        ],
        lldp.OID_LLDP_REM_CHASSIS_ID: [
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.4.1", "aa:aa:aa:aa:aa:aa"),
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.4.2", "bb:bb:bb:bb:bb:bb"),
        ],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert len(neighbors) == 2
    assert all(n["local_port_num"] == "4" for n in neighbors)
    assert {n["remote_index"] for n in neighbors} == {"1", "2"}


@pytest.mark.asyncio
async def test_row_with_nothing_identifying_is_dropped(monkeypatch):
    """A row that only has a port_desc or sys_desc, with neither a
    chassis_id nor a port_id ever answering, isn't a usable neighbor
    identification -- dropped rather than fabricated into a nameless
    neighbor entry."""
    table = {
        lldp.OID_LLDP_REM_SYS_DESC: [(f"{lldp.OID_LLDP_REM_SYS_DESC}.1.9.1", "some description")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors == []


@pytest.mark.asyncio
async def test_empty_device_returns_empty_list(monkeypatch):
    monkeypatch.setattr(lldp, "async_walk", _fake_walk({}))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors == []


def test_rem_index_key_rejects_malformed_suffixes():
    base = lldp.OID_LLDP_REM_CHASSIS_ID
    assert lldp._rem_index_key(f"{base}.1.3.1", base) == ("3", "1")
    assert lldp._rem_index_key(f"{base}.1.3", base) is None, "only two parts -- not a valid 3-part composite index"
    assert lldp._rem_index_key(f"{base}.1.3.1.9", base) is None, "four parts -- not this table's index shape"
    assert lldp._rem_index_key(base, base) is None, "no suffix at all"


@pytest.mark.asyncio
async def test_single_vlan_reported_for_a_neighbor(monkeypatch):
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:bb:cc:dd:ee:ff")],
        # 4-part index: timeMark.localPortNum.remIndex.vlanId -- vlan 42 on port 3, neighbor 1.
        lldp.OID_LLDP_REM_VLAN_NAME: [(f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.3.1.42", "Regie-Audio")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors[0]["vlans"] == [{"id": "42", "name": "Regie-Audio"}]


@pytest.mark.asyncio
async def test_multiple_vlans_on_a_trunk_port_are_all_reported(monkeypatch):
    """A trunk port can legitimately report more than one VLAN for the
    same neighbor -- lldpXdot1RemVlanId is part of the table's index
    precisely to allow this."""
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:bb:cc:dd:ee:ff")],
        lldp.OID_LLDP_REM_VLAN_NAME: [
            (f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.3.1.10", "Data"),
            (f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.3.1.99", "Voice"),
            (f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.3.1.1", "Default"),
        ],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    # Must be sorted numerically by VLAN id (1, 10, 99), not lexically.
    assert neighbors[0]["vlans"] == [
        {"id": "1", "name": "Default"},
        {"id": "10", "name": "Data"},
        {"id": "99", "name": "Voice"},
    ]


@pytest.mark.asyncio
async def test_vlans_do_not_leak_across_different_neighbors(monkeypatch):
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID: [
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:aa:aa:aa:aa:aa"),
            (f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.4.1", "bb:bb:bb:bb:bb:bb"),
        ],
        lldp.OID_LLDP_REM_VLAN_NAME: [
            (f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.3.1.10", "Port3-Vlan"),
            (f"{lldp.OID_LLDP_REM_VLAN_NAME}.1.4.1.20", "Port4-Vlan"),
        ],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    by_port = {n["local_port_num"]: n["vlans"] for n in neighbors}
    assert by_port["3"] == [{"id": "10", "name": "Port3-Vlan"}]
    assert by_port["4"] == [{"id": "20", "name": "Port4-Vlan"}]


@pytest.mark.asyncio
async def test_no_vlan_data_gives_empty_list_not_none(monkeypatch):
    table = {
        lldp.OID_LLDP_REM_CHASSIS_ID: [(f"{lldp.OID_LLDP_REM_CHASSIS_ID}.1.3.1", "aa:bb:cc:dd:ee:ff")],
    }
    monkeypatch.setattr(lldp, "async_walk", _fake_walk(table))
    neighbors = await lldp.async_walk_lldp_neighbors("10.4.1.3", "public")
    assert neighbors[0]["vlans"] == []


def test_rem_vlan_key_requires_exactly_four_parts():
    base = lldp.OID_LLDP_REM_VLAN_NAME
    assert lldp._rem_vlan_key(f"{base}.1.3.1.42", base) == ("3", "1", "42")
    assert lldp._rem_vlan_key(f"{base}.1.3.1", base) is None, "only three parts -- that's the plain rem-table shape, not this one"
    assert lldp._rem_vlan_key(base, base) is None


# --- LldpNeighborMonitor: polling multiple hosts -----------------------

@pytest.mark.asyncio
async def test_monitor_polls_each_host_independently(monkeypatch):
    async def fake_walk_neighbors(host, community, **kwargs):
        return [{"sys_name": f"neighbor-of-{host}"}]
    monkeypatch.setattr(lldp, "async_walk_lldp_neighbors", fake_walk_neighbors)

    monitor = lldp.LldpNeighborMonitor({"10.4.1.3": "GigaCore", "10.4.1.4": "Switch2"}, "public")
    await monitor.async_update()

    snap = monitor.snapshot()
    assert snap["10.4.1.3"] == [{"sys_name": "neighbor-of-10.4.1.3"}]
    assert snap["10.4.1.4"] == [{"sys_name": "neighbor-of-10.4.1.4"}]


@pytest.mark.asyncio
async def test_monitor_unreachable_host_does_not_break_others(monkeypatch):
    async def flaky(host, community, **kwargs):
        if host == "10.4.1.99":
            raise OSError("unreachable")
        return [{"sys_name": "ok"}]
    monkeypatch.setattr(lldp, "async_walk_lldp_neighbors", flaky)

    monitor = lldp.LldpNeighborMonitor({"10.4.1.3": "GigaCore", "10.4.1.99": "Injoignable"}, "public")
    await monitor.async_update()
    assert set(monitor.snapshot().keys()) == {"10.4.1.3"}


@pytest.mark.asyncio
async def test_monitor_no_hosts_is_a_noop():
    monitor = lldp.LldpNeighborMonitor({}, "public")
    await monitor.async_update()
    assert monitor.snapshot() == {}
