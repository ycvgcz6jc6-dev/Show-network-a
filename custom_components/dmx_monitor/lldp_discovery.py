"""Phase C11 (rapport maître, S101): 'Développer réellement: LLDP, port,
VLAN prouvé, ...' -- this module covers LLDP neighbor discovery, using
the standard LLDP-MIB (IEEE 802.1AB / RFC-equivalent, OID base
1.0.8802.1.1.2), present on any switch that supports LLDP regardless of
vendor -- Luminex, Aruba, Cisco, ELC or otherwise.

Read-only GETNEXT walks only (snmp.py's async_walk()); nothing is ever
written to a device, and no LLDP frames are transmitted by Show Network
itself -- this only reads what neighboring switches have already learned
and stored in their own LLDP-MIB.

lldpRemTable's index is composite (lldpRemTimeMark, lldpRemLocalPortNum,
lldpRemIndex) -- three dot-separated integers after each column's base
OID -- unlike IF-MIB's single ifIndex in switch_port_telemetry.py. Rows
are joined on (localPortNum, remIndex); timeMark only reflects the last
topology-change discontinuity and isn't needed to correlate columns
within a single poll.
"""
from __future__ import annotations

import asyncio

from .snmp import async_walk, index_suffix as _index_suffix

# LLDP-MIB (IEEE 802.1AB) remote-systems table -- one row per neighbor
# seen on a local port (a port can see more than one neighbor if it's
# connected through a hub/unmanaged device, hence lldpRemIndex).
OID_LLDP_REM_CHASSIS_ID_SUBTYPE = "1.0.8802.1.1.2.1.4.1.1.4"
OID_LLDP_REM_CHASSIS_ID = "1.0.8802.1.1.2.1.4.1.1.5"
OID_LLDP_REM_PORT_ID_SUBTYPE = "1.0.8802.1.1.2.1.4.1.1.6"
OID_LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"
OID_LLDP_REM_PORT_DESC = "1.0.8802.1.1.2.1.4.1.1.8"
OID_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"
OID_LLDP_REM_SYS_DESC = "1.0.8802.1.1.2.1.4.1.1.10"

# LLDP-MIB local-port table -- maps a local LLDP port number to a
# human-readable local port identifier, so a remote-table row (indexed by
# that same local port number) can be attributed to a named local port
# rather than a bare number. Local port numbering does not always match
# IF-MIB's ifIndex, so this is looked up separately rather than assumed
# equal.
OID_LLDP_LOC_PORT_ID = "1.0.8802.1.1.2.1.3.7.1.3"
OID_LLDP_LOC_PORT_DESC = "1.0.8802.1.1.2.1.3.7.1.4"

# LLDP-EXT-DOT1-MIB (IEEE 802.1AB-2005 Annex F.4) -- "VLAN prouvé" (rapport
# maître S101): the VLAN(s) a neighbor announced for a given port, as
# opposed to a VLAN merely configured/assumed locally. Source-verified
# directly against the published MIB text (two independent mirrors:
# github.com/librenms/librenms and github.com/robison/snmp-config), not
# inferred, given this codebase's standing rule to never guess at an
# undocumented OID. lldpXdot1RemVlanNameEntry's INDEX is a *four*-part
# composite: { lldpRemTimeMark, lldpRemLocalPortNum, lldpRemIndex,
# lldpXdot1RemVlanId } -- one row per (port, neighbor, VLAN), since a
# trunk port can legitimately report more than one VLAN for the same
# neighbor. lldpXdot1RemVlanId itself is NOT-ACCESSIBLE (index-only, entry
# object 1): it never appears as a walkable column, only embedded in the
# OID suffix of lldpXdot1RemVlanName (entry object 2, MAX-ACCESS
# read-only) -- so walking the name column alone yields both the id (from
# the suffix) and the name (the value) for every row.
OID_LLDP_REM_VLAN_NAME = "1.0.8802.1.1.2.1.5.32962.1.3.3.1.2"

_CHASSIS_SUBTYPE_LABELS = {
    1: "chassis_component", 2: "interface_alias", 3: "port_component",
    4: "mac_address", 5: "network_address", 6: "interface_name", 7: "local",
}
_PORT_SUBTYPE_LABELS = {
    1: "interface_alias", 2: "port_component", 3: "mac_address",
    4: "network_address", 5: "interface_name", 6: "agent_circuit_id", 7: "local",
}

_REM_COLUMNS = {
    "chassis_id_subtype": OID_LLDP_REM_CHASSIS_ID_SUBTYPE,
    "chassis_id": OID_LLDP_REM_CHASSIS_ID,
    "port_id_subtype": OID_LLDP_REM_PORT_ID_SUBTYPE,
    "port_id": OID_LLDP_REM_PORT_ID,
    "port_desc": OID_LLDP_REM_PORT_DESC,
    "sys_name": OID_LLDP_REM_SYS_NAME,
    "sys_desc": OID_LLDP_REM_SYS_DESC,
}


def _rem_index_key(oid: str, base: str) -> tuple[str, str] | None:
    """(localPortNum, remIndex) from a lldpRemTable row's OID, dropping
    the leading timeMark component. None if oid isn't a 3-part composite
    index under base at all (a malformed/unexpected row -- skipped rather
    than guessed at)."""
    suffix = _index_suffix(oid, base)
    if suffix is None:
        return None
    parts = suffix.split(".")
    if len(parts) != 3:
        return None
    _time_mark, local_port_num, rem_index = parts
    return (local_port_num, rem_index)


def _rem_vlan_key(oid: str, base: str) -> tuple[str, str, str] | None:
    """(localPortNum, remIndex, vlanId) from a lldpXdot1RemVlanNameTable
    row's OID -- a *four*-part composite index (timeMark, localPortNum,
    remIndex, vlanId), one more component than the base lldpRemTable
    since a single (port, neighbor) pair can report several VLANs."""
    suffix = _index_suffix(oid, base)
    if suffix is None:
        return None
    parts = suffix.split(".")
    if len(parts) != 4:
        return None
    _time_mark, local_port_num, rem_index, vlan_id = parts
    return (local_port_num, rem_index, vlan_id)


async def async_walk_lldp_neighbors(host: str, community: str, *, timeout: float = 1.0,
                                     source_ip: str | None = None, max_rows: int = 128) -> list[dict]:
    """LLDP neighbors this device has learned, one row per (local port,
    neighbor). Each neighbor row identifies the local port it was seen on
    (both the raw local port number and, when available, its own
    human-readable local port id/description from lldpLocPortTable) and
    what the neighbor announced about itself (chassis id, port id,
    port/system description, system name).
    """
    local_port_names: dict[str, str] = {}
    loc_id_rows = await async_walk(host, community, OID_LLDP_LOC_PORT_ID, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
    for oid, value in loc_id_rows:
        idx = _index_suffix(oid, OID_LLDP_LOC_PORT_ID)
        if idx is not None and value:
            local_port_names[idx] = str(value)
    loc_desc_rows = await async_walk(host, community, OID_LLDP_LOC_PORT_DESC, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
    for oid, value in loc_desc_rows:
        idx = _index_suffix(oid, OID_LLDP_LOC_PORT_DESC)
        if idx is not None and idx not in local_port_names and value:
            local_port_names[idx] = str(value)

    neighbors: dict[tuple[str, str], dict] = {}
    for field, base in _REM_COLUMNS.items():
        rows = await async_walk(host, community, base, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
        for oid, value in rows:
            key = _rem_index_key(oid, base)
            if key is None:
                continue
            neighbors.setdefault(key, {"local_port_num": key[0], "rem_index": key[1]})[field] = value

    vlans_by_key: dict[tuple[str, str], list[dict]] = {}
    vlan_rows = await async_walk(host, community, OID_LLDP_REM_VLAN_NAME, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
    for oid, value in vlan_rows:
        vkey = _rem_vlan_key(oid, OID_LLDP_REM_VLAN_NAME)
        if vkey is None:
            continue
        local_port_num, rem_index, vlan_id = vkey
        vlans_by_key.setdefault((local_port_num, rem_index), []).append({"id": vlan_id, "name": value})

    result = []
    for (local_port_num, rem_index), row in neighbors.items():
        if "chassis_id" not in row and "port_id" not in row:
            continue  # nothing identifying at all answered for this row
        chassis_subtype = row.get("chassis_id_subtype")
        port_subtype = row.get("port_id_subtype")
        result.append({
            "local_port_num": local_port_num,
            "local_port_name": local_port_names.get(local_port_num),
            "remote_index": rem_index,
            "chassis_id": row.get("chassis_id"),
            "chassis_id_type": _CHASSIS_SUBTYPE_LABELS.get(chassis_subtype, "unknown") if isinstance(chassis_subtype, int) else "unknown",
            "port_id": row.get("port_id"),
            "port_id_type": _PORT_SUBTYPE_LABELS.get(port_subtype, "unknown") if isinstance(port_subtype, int) else "unknown",
            "port_desc": row.get("port_desc"),
            "sys_name": row.get("sys_name"),
            "sys_desc": row.get("sys_desc"),
            "vlans": sorted(vlans_by_key.get((local_port_num, rem_index), []), key=lambda v: int(v["id"]) if str(v["id"]).isdigit() else 0),
        })
    result.sort(key=lambda n: (int(n["local_port_num"]) if str(n["local_port_num"]).isdigit() else 0, n["remote_index"]))
    return result


class LldpNeighborMonitor:
    """Poll LLDP neighbors for a set of configured switch hosts. Purely a
    collector -- resolving a neighbor's chassis id against the device
    inventory (or minting a synthetic identity for one not yet known) and
    feeding the result into the topology graph is a coordinator-level
    concern (see coordinator.py's _ingest_lldp_neighbors), since it needs
    access to the shared inventory/topology, not just this poll.
    """

    def __init__(self, hosts: dict[str, str | None], community: str):
        self.hosts = dict(hosts)
        self.community = community
        self.by_host: dict[str, list[dict]] = {}

    async def _poll_one(self, host: str) -> tuple[str, list[dict]]:
        return host, await async_walk_lldp_neighbors(host, self.community)

    async def async_update(self) -> None:
        if not self.hosts:
            return
        results = await asyncio.gather(
            *(self._poll_one(host) for host in self.hosts),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                continue
            host, neighbors = result
            self.by_host[host] = neighbors

    def snapshot(self) -> dict[str, list[dict]]:
        return dict(self.by_host)
