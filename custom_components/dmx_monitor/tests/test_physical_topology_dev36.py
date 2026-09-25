from custom_components.dmx_monitor.device_inventory import DeviceInventory
from custom_components.dmx_monitor.device_model import DeviceModel
from custom_components.dmx_monitor.topology import ShowTopology


def test_same_ip_on_two_interfaces_is_not_identity_conflict():
    inv = [
        {"unique_id":"mac:aaaa", "ip":"10.0.0.10", "interface":"eth0", "mac":"aa"},
        {"unique_id":"mac:bbbb", "ip":"10.0.0.10", "interface":"eth1", "mac":"bb"},
    ]
    model = DeviceModel().build(inv, {"nodes":[], "links":[]})
    assert model["conflict_count"] == 0


def test_same_ip_same_interface_still_reports_conflict():
    inv = [
        {"unique_id":"mac:aaaa", "ip":"10.0.0.10", "interface":"eth0", "mac":"aa"},
        {"unique_id":"mac:bbbb", "ip":"10.0.0.10", "interface":"eth0", "mac":"bb"},
    ]
    model = DeviceModel().build(inv, {"nodes":[], "links":[]})
    assert model["conflict_count"] == 1
    assert model["conflicts"][0]["interface"] == "eth0"


def test_topology_keeps_inventory_interface():
    topo = ShowTopology()
    topo.ingest_inventory([{"unique_id":"mac:aaaa", "ip":"10.0.0.10", "interface":"eth9", "confidence_score":1.0}])
    node = next(x for x in topo.snapshot()["nodes"] if x["id"] == "mac:aaaa")
    assert node["interface"] == "eth9"


def test_lldp_physical_path_requires_existing_identity_and_does_not_guess_vlan():
    inv = DeviceInventory()
    dev = inv.upsert(unique_id="candidate:10.0.0.20", ip="10.0.0.20", hostname="amp-a", interface="eth0")
    updated = inv.observe_physical_path(dev.unique_id, switch_name="SW-A", switch_port="1/7", link_speed_mbps=1000, source="LLDP-MIB SW-A")
    assert updated.switch_name == "SW-A"
    assert updated.switch_port == "1/7"
    assert updated.link_speed_mbps == 1000
    assert updated.vlan is None
    assert inv.observe_physical_path("missing", switch_name="SW-A", switch_port="1/8") is None
