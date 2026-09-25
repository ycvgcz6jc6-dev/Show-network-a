"""Reliable local NIC inventory for multi-interface show networks.

Read-only: no route, VLAN, address or interface state is changed.

Extended for Phase C9 (rapport maître, PHASE C9 - MULTI-NIC, S99): per
interface now also exposes IPv4 network/prefix, the default route (if
this interface owns it), and joined multicast groups -- plus a
route_to_target() helper answering "which local interface, if any, would
traffic to this target IP actually use" for known show devices (CEM3,
GigaCore/Luminex, MA, Dante, Reolink, ...). Everything here only reads
/proc; nothing is ever written to routes, addresses or interface state.
"""
from __future__ import annotations
import ipaddress
import socket
from dataclasses import dataclass, asdict, field
from pathlib import Path

@dataclass(frozen=True)
class NetworkInterfaceInfo:
    name: str
    addresses: tuple[str, ...]
    family: tuple[str, ...]
    mac: str | None = None
    is_up: bool | None = None
    speed_mbps: int | None = None
    ipv4_networks: tuple[str, ...] = ()  # CIDR per IPv4 address, e.g. "10.4.1.8/8"
    is_default_route: bool = False
    multicast_groups: tuple[str, ...] = ()

def discover_interfaces() -> list[NetworkInterfaceInfo]:
    default_iface = _default_route_interface()
    multicast_by_iface = _multicast_groups_by_interface()
    try:
        import psutil  # provided by normal HA environments; optional fallback below
        rows=[]
        addrs=psutil.net_if_addrs()
        stats=psutil.net_if_stats()
        AF_LINK=getattr(psutil, "AF_LINK", object())
        for name in sorted(addrs):
            addresses=[]; families=[]; mac=None; networks=[]
            for item in addrs[name]:
                if item.family == socket.AF_INET:
                    addresses.append(item.address); families.append("IPv4")
                    if getattr(item, "netmask", None):
                        try:
                            net = ipaddress.ip_network(f"{item.address}/{item.netmask}", strict=False)
                            networks.append(str(net))
                        except ValueError:
                            pass
                elif item.family == socket.AF_INET6:
                    addresses.append(item.address.split('%')[0]); families.append("IPv6")
                elif item.family == AF_LINK:
                    mac=item.address
            st=stats.get(name)
            rows.append(NetworkInterfaceInfo(
                name, tuple(sorted(set(addresses))), tuple(sorted(set(families))), mac,
                bool(st.isup) if st else None, int(st.speed) if st and st.speed else None,
                tuple(sorted(set(networks))), name == default_iface,
                tuple(sorted(multicast_by_iface.get(name, ()))),
            ))
        return rows
    except Exception:
        pass
    try:
        names=[name for _,name in socket.if_nameindex()]
    except OSError:
        names=[]
    return [NetworkInterfaceInfo(name, (), (), is_default_route=(name == default_iface),
                                 multicast_groups=tuple(sorted(multicast_by_iface.get(name, ()))))
            for name in sorted(names)]

def _hex_to_ip(hexstr: str) -> str:
    """/proc/net/route and /proc/net/igmp store IPv4 addresses as 8 hex
    chars in little-endian byte order (the kernel's native word order on
    x86)."""
    raw = bytes.fromhex(hexstr)[::-1]
    return ".".join(str(b) for b in raw)

def _default_route_interface(path: str = "/proc/net/route") -> str | None:
    """Name of the interface owning the default route (destination
    0.0.0.0/0), or None if it can't be determined. Read-only -- this never
    changes routing."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 8:
            continue
        iface, destination, _gateway, flags = parts[0], parts[1], parts[2], parts[3]
        try:
            if destination == "00000000" and (int(flags, 16) & 0x2):  # RTF_GATEWAY
                return iface
        except ValueError:
            continue
    return None

def read_default_route(path: str = "/proc/net/route") -> dict | None:
    """Full detail of the default route: interface, gateway, metric."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 8:
            continue
        iface, destination, gateway, flags, _refcnt, _use, metric = parts[:7]
        try:
            if destination == "00000000" and (int(flags, 16) & 0x2):
                return {"interface": iface, "gateway": _hex_to_ip(gateway), "metric": int(metric)}
        except ValueError:
            continue
    return None

def _multicast_groups_by_interface(path: str = "/proc/net/igmp") -> dict[str, list[str]]:
    """Joined IPv4 multicast groups, per interface. /proc/net/igmp's format
    interleaves an interface header line (index, name, refcount...) with
    indented group lines (hex group address, refcount, flags) for that
    interface -- track the "current" interface as we walk lines."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return {}
    result: dict[str, list[str]] = {}
    current_iface: str | None = None
    for line in lines[1:]:
        if not line.startswith(("\t", " ")) and ":" in line:
            # Interface header, e.g. "2      enp10s0 : 1     C0A80001 0"
            parts = line.split()
            if len(parts) >= 2:
                current_iface = parts[1]
                result.setdefault(current_iface, [])
            continue
        if current_iface is None:
            continue
        parts = line.split()
        if not parts:
            continue
        group_hex = parts[0]
        if len(group_hex) != 8:
            continue
        try:
            result[current_iface].append(_hex_to_ip(group_hex))
        except ValueError:
            continue
    return result

def route_to_target(interfaces: list[NetworkInterfaceInfo] | None, target_ip: str) -> dict:
    """Which local interface, if any, would traffic to target_ip actually
    use -- same-subnet match first, default route as fallback, otherwise
    reported unreachable. Pure computation from already-gathered
    interface/route data; never sends a packet."""
    try:
        target = ipaddress.ip_address(target_ip)
    except ValueError:
        return {"target": target_ip, "reachable": False, "reason": "invalid_address"}
    rows = interfaces if interfaces is not None else discover_interfaces()
    for row in rows:
        for net_str in row.ipv4_networks:
            try:
                net = ipaddress.ip_network(net_str, strict=False)
            except ValueError:
                continue
            if target in net:
                return {"target": target_ip, "reachable": True, "interface": row.name,
                        "via": "same_subnet", "network": net_str}
    default_route = read_default_route()
    if default_route:
        return {"target": target_ip, "reachable": True, "interface": default_route["interface"],
                "via": "default_gateway", "gateway": default_route["gateway"]}
    return {"target": target_ip, "reachable": False, "reason": "no_matching_subnet_and_no_default_route"}

def snapshot() -> list[dict]:
    return [asdict(item) for item in discover_interfaces()]

