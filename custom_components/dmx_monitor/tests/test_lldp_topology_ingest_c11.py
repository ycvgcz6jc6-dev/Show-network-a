"""Phase C11 (rapport maître, S101): coordinator-level LLDP-to-topology
integration. device_model.py's physical_links filter has always
specifically looked for protocol=="LLDP" -- this is the previously
missing data source for it.
"""
from __future__ import annotations

from custom_components.dmx_monitor.coordinator import ShowNetworkCoordinator
from custom_components.dmx_monitor.device_inventory import DeviceInventory
from custom_components.dmx_monitor.topology import ShowTopology


def test_coordinator_ingests_lldp_neighbors_into_topology():
    """A neighbor already known to the inventory by MAC resolves to the
    *same* topology node id the inventory itself uses, not a separate
    duplicate identity."""
    inventory = DeviceInventory(None)
    # The LLDP neighbor below announces this same MAC as its chassis id.
    known = inventory.upsert(ip="10.4.1.50", mac="AA:BB:CC:DD:EE:FF", unique_id="candidate:10.4.1.50")
    assert known.unique_id == "mac:aabbccddeeff"  # promoted by mac, confirms the id this test relies on

    class _FakeLldpMonitor:
        def snapshot(self):
            return {
                "10.4.1.3": [  # the switch's own IP
                    {  # neighbor #1: matches the known inventory device by MAC
                        "local_port_num": "3", "local_port_name": "Gi0/3", "remote_index": "1",
                        "chassis_id": "aa:bb:cc:dd:ee:ff", "chassis_id_type": "mac_address",
                        "port_id": "eth0", "port_id_type": "interface_name",
                        "sys_name": "known-device", "port_desc": None, "sys_desc": None,
                    },
                    {  # neighbor #2: not in inventory at all -- must get a synthetic id, not crash
                        "local_port_num": "4", "local_port_name": "Gi0/4", "remote_index": "1",
                        "chassis_id": "11:22:33:44:55:66", "chassis_id_type": "mac_address",
                        "port_id": "eth1", "port_id_type": "interface_name",
                        "sys_name": "unknown-device", "port_desc": None, "sys_desc": None,
                    },
                ],
            }

    class _FakeSelf:
        pass

    fake = _FakeSelf()
    fake.lldp_monitor = _FakeLldpMonitor()
    fake.inventory = inventory
    fake.topology = ShowTopology()

    ShowNetworkCoordinator._ingest_lldp_neighbors(fake)

    snap = fake.topology.snapshot()
    links_by_target = {l["target"]: l for l in snap["links"]}

    known_link = links_by_target["mac:aabbccddeeff"]
    assert known_link["source"] == "candidate:10.4.1.3"
    assert known_link["source_port"] == "Gi0/3"
    assert known_link["target_port"] == "eth0"
    assert known_link["protocol"] == "LLDP"

    synthetic_link = links_by_target["lldp:11:22:33:44:55:66"]
    assert synthetic_link["source"] == "candidate:10.4.1.3"
    assert synthetic_link["protocol"] == "LLDP"


def test_lldp_ingest_updates_not_duplicates_on_repeated_polls():
    """Calling _ingest_lldp_neighbors again with the same neighbor still
    present must update the existing link (topology.observe_link's own
    dedup key), not create a second one -- otherwise every refresh cycle
    would grow the link list forever."""

    class _FakeLldpMonitor:
        def snapshot(self):
            return {"10.4.1.3": [{
                "local_port_num": "3", "local_port_name": "Gi0/3", "remote_index": "1",
                "chassis_id": "11:22:33:44:55:66", "chassis_id_type": "mac_address",
                "port_id": "eth0", "port_id_type": "interface_name",
                "sys_name": "device", "port_desc": None, "sys_desc": None,
            }]}

    class _FakeSelf:
        pass

    fake = _FakeSelf()
    fake.lldp_monitor = _FakeLldpMonitor()
    fake.inventory = DeviceInventory(None)
    fake.topology = ShowTopology()

    ShowNetworkCoordinator._ingest_lldp_neighbors(fake)
    ShowNetworkCoordinator._ingest_lldp_neighbors(fake)

    assert len(fake.topology.snapshot()["links"]) == 1


def test_non_mac_chassis_id_always_gets_synthetic_identity():
    """A chassis id that isn't a MAC address (e.g. a chassis component
    id, or a network address) can never match the inventory's mac:-based
    identity scheme -- must still produce a usable synthetic node rather
    than being dropped or crashing."""

    class _FakeLldpMonitor:
        def snapshot(self):
            return {"10.4.1.3": [{
                "local_port_num": "1", "local_port_name": None, "remote_index": "1",
                "chassis_id": "chassis-serial-12345", "chassis_id_type": "chassis_component",
                "port_id": "1", "port_id_type": "local",
                "sys_name": None, "port_desc": None, "sys_desc": None,
            }]}

    class _FakeSelf:
        pass

    fake = _FakeSelf()
    fake.lldp_monitor = _FakeLldpMonitor()
    fake.inventory = DeviceInventory(None)
    fake.topology = ShowTopology()

    ShowNetworkCoordinator._ingest_lldp_neighbors(fake)

    links = fake.topology.snapshot()["links"]
    assert len(links) == 1
    assert links[0]["target"] == "lldp:chassis-serial-12345"


def test_lowest_vlan_id_used_as_the_link_representative():
    """topology.TopologyLink has a single `vlan` slot; a trunk port
    reporting several VLANs for one neighbor must pick a consistent,
    deterministic representative (the lowest id), not whichever the walk
    happened to return last."""
    from custom_components.dmx_monitor.coordinator import _lowest_vlan_id

    assert _lowest_vlan_id(None) is None
    assert _lowest_vlan_id([]) is None
    assert _lowest_vlan_id([{"id": "10", "name": "Data"}]) == 10
    assert _lowest_vlan_id([{"id": "99", "name": "Voice"}, {"id": "1", "name": "Default"}, {"id": "10", "name": "Data"}]) == 1


def test_vlan_propagated_from_neighbor_into_topology_link():
    class _FakeLldpMonitor:
        def snapshot(self):
            return {"10.4.1.3": [{
                "local_port_num": "3", "local_port_name": "Gi0/3", "remote_index": "1",
                "chassis_id": "11:22:33:44:55:66", "chassis_id_type": "mac_address",
                "port_id": "eth0", "port_id_type": "interface_name",
                "sys_name": "device", "port_desc": None, "sys_desc": None,
                "vlans": [{"id": "99", "name": "Voice"}, {"id": "10", "name": "Data"}],
            }]}

    class _FakeSelf:
        pass

    fake = _FakeSelf()
    fake.lldp_monitor = _FakeLldpMonitor()
    fake.inventory = DeviceInventory(None)
    fake.topology = ShowTopology()

    ShowNetworkCoordinator._ingest_lldp_neighbors(fake)

    link = fake.topology.snapshot()["links"][0]
    assert link["vlan"] == 10, "must be the lowest of the reported VLANs (10, not 99)"
