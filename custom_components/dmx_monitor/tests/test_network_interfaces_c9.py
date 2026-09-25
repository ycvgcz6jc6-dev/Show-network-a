"""Phase C9 (rapport maître, S99): per-interface routes, multicast groups,
and route_to_target(). Uses real /proc/net/route and /proc/net/igmp text
formats (little-endian hex IPv4, exactly as the Linux kernel writes them)
so the hex-decoding itself is under test, not just the surrounding logic.
"""
from __future__ import annotations

from custom_components.dmx_monitor.network_interfaces import (
    NetworkInterfaceInfo,
    _default_route_interface,
    _hex_to_ip,
    _multicast_groups_by_interface,
    read_default_route,
    route_to_target,
)


def test_hex_to_ip_decodes_little_endian_kernel_format():
    # 10.4.1.8 as the kernel writes it: little-endian byte order.
    assert _hex_to_ip("0801040A") == "10.4.1.8"
    assert _hex_to_ip("00000000") == "0.0.0.0"


def test_default_route_interface_and_full_detail(tmp_path):
    route_file = tmp_path / "route"
    # Real /proc/net/route shape: header + tab-separated fields.
    # Default route (Destination 00000000) via enp3s0f0, gateway 10.1.1.1, metric 100.
    route_file.write_text(
        "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
        "enp3s0f0\t00000000\t0101010A\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
        "enp10s0\t0801040A\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0\n"
    )
    assert _default_route_interface(str(route_file)) == "enp3s0f0"
    detail = read_default_route(str(route_file))
    assert detail == {"interface": "enp3s0f0", "gateway": "10.1.1.1", "metric": 100}


def test_default_route_absent_returns_none(tmp_path):
    route_file = tmp_path / "route"
    route_file.write_text(
        "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
        "enp10s0\t0801040A\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0\n"
    )
    assert _default_route_interface(str(route_file)) is None
    assert read_default_route(str(route_file)) is None


def test_default_route_file_missing_is_handled_gracefully(tmp_path):
    missing = tmp_path / "does_not_exist"
    assert _default_route_interface(str(missing)) is None
    assert read_default_route(str(missing)) is None


def test_multicast_groups_parsed_per_interface(tmp_path):
    igmp_file = tmp_path / "igmp"
    # Real /proc/net/igmp shape: an interface header line (not indented),
    # then one indented line per joined group for that interface.
    igmp_file.write_text(
        "Idx\tDevice    : Count Querier\tGroup    Users Timer\tReporter\n"
        "1\tenp10s0\t\t: 2     V3\n"
        "\t\t\t\tFB0000EF\t1    0:00000000\t\t0\n"
        "\t\t\t\t0100FFEF\t1    0:00000000\t\t0\n"
        "2\tenp3s0f0\t\t: 1     V3\n"
        "\t\t\t\t0100005E\t1    0:00000000\t\t0\n"
    )
    groups = _multicast_groups_by_interface(str(igmp_file))
    assert set(groups["enp10s0"]) == {"239.0.0.251", "239.255.0.1"}
    assert groups["enp3s0f0"] == ["94.0.0.1"]


def test_route_to_target_same_subnet_match():
    interfaces = [
        NetworkInterfaceInfo(
            name="enp10s0", addresses=("10.4.1.8",), family=("IPv4",),
            ipv4_networks=("10.4.1.8/24",),
        ),
        NetworkInterfaceInfo(
            name="enp3s0f0", addresses=("192.168.0.57",), family=("IPv4",),
            ipv4_networks=("192.168.0.57/24",),
        ),
    ]
    result = route_to_target(interfaces, "10.4.1.3")  # the GigaCore in the audit's own baseline
    assert result == {
        "target": "10.4.1.3", "reachable": True, "interface": "enp10s0",
        "via": "same_subnet", "network": "10.4.1.8/24",
    }


def test_route_to_target_falls_back_to_default_gateway(tmp_path, monkeypatch):
    route_file = tmp_path / "route"
    route_file.write_text(
        "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
        "enp3s0f0\t00000000\t0101010A\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
    )
    import custom_components.dmx_monitor.network_interfaces as ni
    original_read_default_route = ni.read_default_route
    monkeypatch.setattr(ni, "read_default_route", lambda: original_read_default_route(str(route_file)))

    interfaces = [
        NetworkInterfaceInfo(name="enp10s0", addresses=("10.4.1.8",), family=("IPv4",), ipv4_networks=("10.4.1.8/24",)),
    ]
    # 8.8.8.8 matches no local subnet -- must fall back to the default route.
    result = route_to_target(interfaces, "8.8.8.8")
    assert result["reachable"] is True
    assert result["via"] == "default_gateway"
    assert result["interface"] == "enp3s0f0"
    assert result["gateway"] == "10.1.1.1"


def test_route_to_target_unreachable_with_no_default_route(monkeypatch):
    import custom_components.dmx_monitor.network_interfaces as ni
    monkeypatch.setattr(ni, "read_default_route", lambda: None)

    interfaces = [
        NetworkInterfaceInfo(name="enp10s0", addresses=("10.4.1.8",), family=("IPv4",), ipv4_networks=("10.4.1.8/24",)),
    ]
    result = route_to_target(interfaces, "203.0.113.5")
    assert result == {
        "target": "203.0.113.5", "reachable": False,
        "reason": "no_matching_subnet_and_no_default_route",
    }


def test_route_to_target_rejects_invalid_address():
    result = route_to_target([], "not-an-ip")
    assert result == {"target": "not-an-ip", "reachable": False, "reason": "invalid_address"}


def test_coordinator_computes_routes_for_known_and_discovered_targets():
    """Coordinator._compute_route_to_targets: the curated-target list
    behind Phase C9's 'route to target pour CEM3, Dante, Luminex, MA,
    Reolink, etc.' -- explicit GigaCore/CEM3 config hosts, plus every
    inventory device with an IP (covering Dante/MA/Reolink/etc without
    needing a dedicated config key for each)."""
    from custom_components.dmx_monitor.coordinator import ShowNetworkCoordinator

    class _Gigacore:
        hosts = ["10.4.1.3"]

    class _Cem3:
        hosts = ["10.4.1.2"]

    class _Inventory:
        def public(self):
            return [
                {"ip": "10.3.2.1", "display_name": "Reolink caméra scène"},
                {"ip": None, "display_name": "Sans IP -- doit être ignoré"},
                {"ip": "10.4.1.3", "display_name": "Doublon GigaCore -- déjà présent, ne doit pas écraser le libellé explicite"},
            ]

    class _FakeSelf:
        gigacore = _Gigacore()
        etc_cem3_monitor = _Cem3()
        inventory = _Inventory()

    interfaces_snapshot = [
        {"name": "enp10s0", "addresses": ("10.4.1.8",), "family": ("IPv4",),
         "ipv4_networks": ("10.4.1.8/24",)},
        {"name": "enp3s0f0", "addresses": ("10.3.2.5",), "family": ("IPv4",),
         "ipv4_networks": ("10.3.2.5/24",)},
    ]

    results = ShowNetworkCoordinator._compute_route_to_targets(_FakeSelf(), interfaces_snapshot)
    by_ip = {r["target"]: r for r in results}

    assert by_ip["10.4.1.3"]["label"] == "Luminex GigaCore", "explicit config label must win over an inventory duplicate"
    assert by_ip["10.4.1.3"]["reachable"] is True
    assert by_ip["10.4.1.3"]["interface"] == "enp10s0"

    assert by_ip["10.4.1.2"]["label"] == "ETC CEM3"
    assert by_ip["10.3.2.1"]["label"] == "Reolink caméra scène"
    assert by_ip["10.3.2.1"]["interface"] == "enp3s0f0"

    assert len(results) == 3, "the IP-less inventory device must be skipped, and the GigaCore duplicate must not appear twice"
