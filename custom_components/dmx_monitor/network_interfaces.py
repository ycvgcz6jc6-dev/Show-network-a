"""Reliable local NIC inventory for multi-interface show networks.

Read-only: no route, VLAN, address or interface state is changed.
"""
from __future__ import annotations
import logging
import socket
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class NetworkInterfaceInfo:
    name: str
    addresses: tuple[str, ...]
    family: tuple[str, ...]
    mac: str | None = None
    is_up: bool | None = None
    speed_mbps: int | None = None

def discover_interfaces() -> list[NetworkInterfaceInfo]:
    try:
        import psutil  # provided by normal HA environments; optional fallback below
        rows=[]
        addrs=psutil.net_if_addrs()
        stats=psutil.net_if_stats()
        AF_LINK=getattr(psutil, "AF_LINK", object())
        for name in sorted(addrs):
            addresses=[]; families=[]; mac=None
            for item in addrs[name]:
                if item.family == socket.AF_INET:
                    addresses.append(item.address); families.append("IPv4")
                elif item.family == socket.AF_INET6:
                    addresses.append(item.address.split('%')[0]); families.append("IPv6")
                elif item.family == AF_LINK:
                    mac=item.address
            st=stats.get(name)
            rows.append(NetworkInterfaceInfo(name, tuple(sorted(set(addresses))), tuple(sorted(set(families))), mac,
                                             bool(st.isup) if st else None, int(st.speed) if st and st.speed else None))
        return rows
    except Exception:
        logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
    try:
        names=[name for _,name in socket.if_nameindex()]
    except OSError:
        names=[]
    return [NetworkInterfaceInfo(name, (), ()) for name in sorted(names)]

def snapshot() -> list[dict]:
    return [asdict(item) for item in discover_interfaces()]
