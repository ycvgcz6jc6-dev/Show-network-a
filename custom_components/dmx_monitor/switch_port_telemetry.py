"""Phase C11 (rapport maître, S101): 'Développer réellement: LLDP, port,
VLAN prouvé, speed, errors, temperature, traffic, PoE, last seen.'

This module covers the port/speed/errors/traffic part using IF-MIB
(RFC 1213/2863), a standard MIB present on any SNMP-managed switch --
Luminex, Aruba, Cisco, ELC or otherwise, no vendor-private OID needed.
It builds on snmp.py's already-existing async_walk() (a bounded, read-
only SNMPv1 GETNEXT walk; no SET). switch_monitor.py deliberately used
GET only and left per-port tables for later ("out of scope for this
GET-only module") -- this is that later.

LLDP neighbor discovery and per-port PoE/VLAN are not covered here yet
(LLDP-MIB's table has a composite index that needs its own correlation
logic); this module is the port/speed/errors/traffic foundation they
would sit alongside.
"""
from __future__ import annotations

import asyncio
from time import monotonic

from .snmp import async_walk, index_suffix as _index_suffix
from .switch_temperature import async_walk_temperature_sensors

# IF-MIB (RFC 2863) -- standard on any SNMP-managed switch.
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"       # bps, 32-bit (caps at ~4.29 Gbps)
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
OID_IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"

_OPER_STATUS_LABELS = {
    1: "up", 2: "down", 3: "testing", 4: "unknown", 5: "dormant",
    6: "not_present", 7: "lower_layer_down",
}

_COLUMNS = {
    "descr": OID_IF_DESCR,
    "oper_status_raw": OID_IF_OPER_STATUS,
    "speed_bps": OID_IF_SPEED,
    "in_errors": OID_IF_IN_ERRORS,
    "out_errors": OID_IF_OUT_ERRORS,
    "in_octets": OID_IF_IN_OCTETS,
    "out_octets": OID_IF_OUT_OCTETS,
}


async def async_walk_if_table(host: str, community: str, *, timeout: float = 1.0,
                               source_ip: str | None = None, max_rows: int = 128) -> list[dict]:
    """Per-port telemetry from IF-MIB: name, oper status, speed, error
    counters, traffic counters. Read-only GETNEXT walks only; nothing is
    ever written to the device.

    Each of the seven columns is its own bounded walk (SNMPv1 has no
    native GETBULK), joined afterward by the shared ifIndex suffix each
    row's OID carries -- a port only appears in the result if at least
    ifDescr answered for it (the anchor column; a port with no name at
    all isn't something Show Network can usefully label as an interface).
    """
    ports: dict[str, dict] = {}
    for field, base in _COLUMNS.items():
        rows = await async_walk(host, community, base, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
        for oid, value in rows:
            idx = _index_suffix(oid, base)
            if idx is None:
                continue
            ports.setdefault(idx, {"index": idx})[field] = value

    result = []
    for idx, row in ports.items():
        if "descr" not in row:
            continue  # no name answered for this index -- not a usable port row
        oper_raw = row.get("oper_status_raw")
        speed_bps = row.get("speed_bps")
        result.append({
            "index": idx,
            "name": row.get("descr"),
            "oper_status": _OPER_STATUS_LABELS.get(oper_raw, "unknown") if isinstance(oper_raw, int) else "unknown",
            "speed_mbps": (speed_bps // 1_000_000) if isinstance(speed_bps, int) else None,
            "rx_errors": row.get("in_errors") if isinstance(row.get("in_errors"), int) else None,
            "tx_errors": row.get("out_errors") if isinstance(row.get("out_errors"), int) else None,
            "rx_octets": row.get("in_octets") if isinstance(row.get("in_octets"), int) else None,
            "tx_octets": row.get("out_octets") if isinstance(row.get("out_octets"), int) else None,
        })
    result.sort(key=lambda p: int(p["index"]) if str(p["index"]).isdigit() else 0)
    return result


# POWER-ETHERNET-MIB (RFC 3621) -- "PoE lorsque disponible" (rapport
# maître S101). Source-verified against oidref.com's per-object OID pages
# (each showing the object's exact numeric position, not inferred from
# the SEQUENCE listing alone) rather than guessed. This table's index is
# { pethPsePortGroupIndex, pethPsePortIndex } -- two integers, since PSE
# ports can be organized into groups on modular/chassis switches; RFC
# 3621 itself notes port numbering within a group is "implementation
# specific", so this is NOT assumed to line up with IF-MIB's ifIndex and
# is reported as its own list rather than merged into async_walk_if_table's
# port rows.
#
# The base standard MIB has no per-port wattage/power-consumption object
# at all -- only a detection/delivery *status*. Real-time per-port watts
# is vendor-specific (no OID for it is publicly documented in this
# project, so none is guessed at here, consistent with switch_monitor.py's
# own stated policy).
OID_PETH_PSE_PORT_ADMIN_ENABLE = "1.3.6.1.2.1.105.1.1.1.3"
OID_PETH_PSE_PORT_DETECTION_STATUS = "1.3.6.1.2.1.105.1.1.1.6"

_POE_DETECTION_STATUS_LABELS = {
    1: "disabled", 2: "searching", 3: "delivering_power",
    4: "fault", 5: "test", 6: "other_fault",
}


def _peth_port_key(oid: str, base: str) -> tuple[str, str] | None:
    """(groupIndex, portIndex) from a pethPsePortTable row's OID -- a
    2-part composite index, RFC 3621's own INDEX clause."""
    suffix = _index_suffix(oid, base)
    if suffix is None:
        return None
    parts = suffix.split(".")
    if len(parts) != 2:
        return None
    group_index, port_index = parts
    return (group_index, port_index)


async def async_walk_poe_ports(host: str, community: str, *, timeout: float = 1.0,
                                source_ip: str | None = None, max_rows: int = 128) -> list[dict]:
    """Per-port PoE status from POWER-ETHERNET-MIB: whether PoE is
    administratively enabled, and the detection/delivery state (does this
    port currently have a Powered Device attached and receiving power).
    Read-only GETNEXT walks only; nothing is ever written to a device
    (AdminEnable is read-write in the MIB, but only ever read here).
    """
    ports: dict[tuple[str, str], dict] = {}
    for field, base in {"admin_enabled_raw": OID_PETH_PSE_PORT_ADMIN_ENABLE, "detection_status_raw": OID_PETH_PSE_PORT_DETECTION_STATUS}.items():
        rows = await async_walk(host, community, base, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
        for oid, value in rows:
            key = _peth_port_key(oid, base)
            if key is None:
                continue
            ports.setdefault(key, {"group_index": key[0], "port_index": key[1]})[field] = value

    result = []
    for (group_index, port_index), row in ports.items():
        if "detection_status_raw" not in row:
            continue  # nothing answered for this index at all
        status_raw = row.get("detection_status_raw")
        admin_raw = row.get("admin_enabled_raw")
        result.append({
            "group_index": group_index,
            "port_index": port_index,
            "admin_enabled": (admin_raw == 1) if isinstance(admin_raw, int) else None,
            "detection_status": _POE_DETECTION_STATUS_LABELS.get(status_raw, "unknown") if isinstance(status_raw, int) else "unknown",
            "delivering_power": status_raw == 3,
        })
    result.sort(key=lambda p: (int(p["group_index"]) if str(p["group_index"]).isdigit() else 0,
                                int(p["port_index"]) if str(p["port_index"]).isdigit() else 0))
    return result


class SwitchPortMonitor:
    """Poll IF-MIB per-port telemetry for a set of configured switch
    hosts, computing rx/tx Mbps rates between successive polls (a single
    walk only gives cumulative octet counters; a rate needs two samples
    and the elapsed time between them). Assembles the switch_telemetry
    shape consumers already expect and defensively read (coordinator.py's
    watchdog-style port-change journal, doctor.py's port-error/bandwidth
    checks, show_snapshot.py's port-fact comparison) but that nothing
    ever actually populated -- switch_telemetry was a live placeholder,
    always empty, until this.
    """

    def __init__(self, hosts: dict[str, str | None], community: str, *, source_ip: str | None = None):
        """``hosts`` maps host/IP -> display name (or None to fall back
        to the IP itself when building each switch's row)."""
        self.hosts = dict(hosts)
        self.community = community
        self.source_ip = source_ip if source_ip not in (None, "", "0.0.0.0") else None
        self._previous: dict[str, dict[str, dict]] = {}
        self.switches: list[dict] = []

    async def _poll_one(self, host: str, name: str | None, now: float) -> dict:
        ports_raw = await async_walk_if_table(host, self.community, source_ip=self.source_ip)
        poe_raw = await async_walk_poe_ports(host, self.community, source_ip=self.source_ip)
        temperature_raw = await async_walk_temperature_sensors(host, self.community, source_ip=self.source_ip)
        prev = self._previous.setdefault(host, {})
        ports = []
        for p in ports_raw:
            idx = p["index"]
            rx_mbps = tx_mbps = None
            prev_p = prev.get(idx)
            if prev_p is not None and prev_p.get("ts") is not None:
                dt = now - prev_p["ts"]
                if dt > 0:
                    rx_mbps = _rate_mbps(prev_p.get("rx_octets"), p.get("rx_octets"), dt)
                    tx_mbps = _rate_mbps(prev_p.get("tx_octets"), p.get("tx_octets"), dt)
            ports.append({**p, "up": p["oper_status"] == "up", "rx_mbps": rx_mbps, "tx_mbps": tx_mbps})
            prev[idx] = {"rx_octets": p.get("rx_octets"), "tx_octets": p.get("tx_octets"), "ts": now}
        # PSE port numbering is "implementation specific" per RFC 3621
        # itself and not assumed to match IF-MIB's ifIndex (see
        # async_walk_poe_ports's own docstring) -- kept as its own list
        # rather than merged into `ports` above.
        return {"name": name or host, "ip": host, "interface": self.source_ip, "ports": ports, "poe_ports": poe_raw, "temperature_sensors": temperature_raw}

    async def async_update(self) -> None:
        if not self.hosts:
            return
        now = monotonic()
        results = await asyncio.gather(
            *(self._poll_one(host, name, now) for host, name in self.hosts.items()),
            return_exceptions=True,
        )
        self.switches = [r for r in results if not isinstance(r, Exception)]

    def snapshot(self) -> list[dict]:
        return self.switches


def _rate_mbps(previous_octets, current_octets, elapsed_s: float) -> float | None:
    """Mbps between two octet-counter samples. IF-MIB counters are
    monotonic and can wrap or reset (device reboot); a negative delta is
    exactly that, not a real negative traffic rate, so it's reported as
    unavailable for this sample rather than as a nonsensical number."""
    if previous_octets is None or current_octets is None:
        return None
    delta = current_octets - previous_octets
    if delta < 0:
        return None
    return round((delta * 8) / elapsed_s / 1_000_000, 3)
