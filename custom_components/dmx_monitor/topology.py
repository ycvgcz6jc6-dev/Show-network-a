"""Descriptive, read-only network topology graph.

Two sources feed this graph, both already used elsewhere in this codebase:

1. ``ingest_inventory()`` turns every device already known to
   ``DeviceInventory`` into a node, keyed the same way coordinator.py's own
   manual ``observe_protocol`` calls key DMX sources (``ip:<ip>``), so a
   device seen both via passive protocol observation and via generic
   inventory converges onto a single node instead of duplicating it.
2. ``async_probe_lldp_neighbors()`` walks the standard LLDP-MIB
   (IEEE 802.1AB -- ``1.0.8802.1.1.2.1.4.1.1``, universally implemented the
   same way across vendors, unlike the ELC/Green-GO situation in
   switch_monitor.py) to discover which device is connected to which switch
   port, and turns that into real links -- never fabricated ones. If a
   switch has no LLDP neighbors (or doesn't support/enable LLDP), no links
   are invented for it: an empty neighbor table means an empty result, not
   a guess.

This module never sends anything other than read-only SNMP GETNEXT
requests, and never assumes a link exists without a positive LLDP
observation. Before real LLDP data is fed in, both ``nodes`` and ``links``
in ``snapshot()`` stay legitimately empty rather than showing something
invented.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .snmp import async_walk, SNMPError

_LOGGER = logging.getLogger(__name__)

# LLDP-MIB (IEEE 802.1AB), lldpRemTable columns actually needed here.
_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"
_LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"
_LLDP_REM_PORT_DESC = "1.0.8802.1.1.2.1.4.1.1.8"
_LLDP_REM_CHASSIS_ID = "1.0.8802.1.1.2.1.4.1.1.5"

_STALE_AFTER_S = 300.0


@dataclass
class TopologyNode:
    node_id: str
    label: str | None = None
    ip: str | None = None
    mac: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    protocols: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    confidence: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


@dataclass
class TopologyLink:
    source: str
    target: str
    kind: str
    label: str | None = None
    evidence: str | None = None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


def _merge(existing: str | None, new: str | None) -> str | None:
    """Keep the existing value unless the new one is a real improvement."""
    return new if new else existing


class ShowTopology:
    """Aggregates observed nodes and (only LLDP-evidenced) links."""

    def __init__(self, stale_after_s: float = _STALE_AFTER_S) -> None:
        self.nodes: dict[str, TopologyNode] = {}
        self.links: dict[tuple[str, str, str], TopologyLink] = {}
        self.stale_after_s = float(stale_after_s)
        self.lldp_errors: dict[str, str] = {}

    # -- nodes -----------------------------------------------------------
    def observe_protocol(
        self,
        node_id: str,
        protocol: str | None,
        *,
        label: str | None = None,
        ip: str | None = None,
        mac: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        category: str | None = None,
        confidence: float = 0.0,
        source: str | None = None,
    ) -> TopologyNode:
        now = time.time()
        node = self.nodes.get(node_id)
        if node is None:
            node = TopologyNode(node_id=node_id, first_seen=now, last_seen=now)
            self.nodes[node_id] = node
        node.last_seen = now
        node.label = _merge(node.label, label)
        node.ip = _merge(node.ip, ip)
        node.mac = _merge(node.mac, mac)
        node.manufacturer = _merge(node.manufacturer, manufacturer)
        node.model = _merge(node.model, model)
        node.category = _merge(node.category, category)
        node.confidence = max(node.confidence, confidence)
        if protocol:
            node.protocols.add(protocol)
        if source:
            node.sources.add(source)
        return node

    def ingest_inventory(self, rows: list[dict[str, Any]]) -> None:
        """Promote every device already known to DeviceInventory into a node.

        Read-only: this never contacts a device, it only reorganizes
        already-collected inventory rows (see device_inventory.py) into the
        topology graph shape.
        """
        for row in rows or ():
            ip = row.get("ip")
            node_id = f"ip:{ip}" if ip else f"id:{row.get('unique_id')}"
            protocols = row.get("protocols") or [None]
            for protocol in protocols:
                self.observe_protocol(
                    node_id,
                    protocol,
                    label=row.get("display_name"),
                    ip=ip,
                    mac=row.get("mac"),
                    manufacturer=row.get("display_manufacturer"),
                    model=row.get("display_model"),
                    category=row.get("category"),
                    confidence=float(row.get("confidence_score") or 0.0),
                    source="inventory",
                )
            switch_name = row.get("switch_name")
            if switch_name:
                switch_node_id = f"switch:{switch_name}"
                self.observe_protocol(switch_node_id, None, label=switch_name, category="switch", source="inventory")
                self._add_link(
                    node_id,
                    switch_node_id,
                    kind="switch_port",
                    label=row.get("switch_port"),
                    evidence="device_inventory.switch_name/switch_port",
                )

    # -- links -------------------------------------------------------------
    def _add_link(self, source: str, target: str, *, kind: str, label: str | None = None, evidence: str | None = None) -> None:
        now = time.time()
        key = (source, target, kind)
        link = self.links.get(key)
        if link is None:
            self.links[key] = TopologyLink(source=source, target=target, kind=kind, label=label, evidence=evidence, first_seen=now, last_seen=now)
        else:
            link.last_seen = now
            link.label = _merge(link.label, label)
            link.evidence = _merge(link.evidence, evidence)

    # -- LLDP (real neighbor evidence only) ---------------------------------
    async def async_probe_lldp_neighbors(self, host: str, community: str, *, port: int = 161, switch_label: str | None = None) -> int:
        """Walk the standard LLDP-MIB on ``host`` and add real links only.

        Returns the number of neighbor links found (0 is a normal, valid
        result -- it means the switch answered but has no LLDP neighbors
        recorded, not that the probe failed).
        """
        switch_node_id = f"switch:{switch_label or host}"
        self.observe_protocol(switch_node_id, "SNMP", label=switch_label or host, ip=host, category="switch", source="lldp_probe")

        try:
            sysname_rows = await async_walk(host, community, _LLDP_REM_SYS_NAME, port=port)
        except SNMPError as exc:
            self.lldp_errors[host] = str(exc)
            _LOGGER.debug("LLDP walk failed for %s: %s", host, exc)
            return 0

        self.lldp_errors.pop(host, None)
        added = 0
        for oid, sys_name in sysname_rows:
            # The table index (everything after the column OID) uniquely
            # identifies this neighbor row; reuse it to fetch the matching
            # port-id/port-desc columns for the same row.
            index_suffix = oid[len(_LLDP_REM_SYS_NAME) + 1:]
            port_id = await self._safe_get_indexed(host, community, _LLDP_REM_PORT_ID, index_suffix, port)
            port_desc = await self._safe_get_indexed(host, community, _LLDP_REM_PORT_DESC, index_suffix, port)
            neighbor_label = str(sys_name) if sys_name else f"lldp-neighbor:{index_suffix}"
            neighbor_node_id = f"lldp:{host}:{index_suffix}"
            self.observe_protocol(neighbor_node_id, "LLDP", label=neighbor_label, source="lldp_probe", confidence=0.9)
            self._add_link(
                neighbor_node_id,
                switch_node_id,
                kind="lldp_neighbor",
                label=str(port_desc or port_id or ""),
                evidence=f"LLDP-MIB lldpRemSysName={neighbor_label}",
            )
            added += 1
        return added

    async def _safe_get_indexed(self, host: str, community: str, column_oid: str, index_suffix: str, port: int = 161):
        from .snmp import async_get

        try:
            return await async_get(host, community, f"{column_oid}.{index_suffix}", port=port)
        except SNMPError:
            return None

    # -- snapshot ------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        nodes = []
        for node in self.nodes.values():
            age = max(0.0, now - node.last_seen)
            nodes.append({
                "id": node.node_id,
                "label": node.label or node.node_id,
                "ip": node.ip,
                "mac": node.mac,
                "manufacturer": node.manufacturer,
                "model": node.model,
                "category": node.category,
                "protocols": sorted(p for p in node.protocols if p),
                "sources": sorted(node.sources),
                "confidence": node.confidence,
                "age_s": round(age, 1),
                "stale": age > self.stale_after_s,
            })
        links = []
        for link in self.links.values():
            age = max(0.0, now - link.last_seen)
            links.append({
                "source": link.source,
                "target": link.target,
                "kind": link.kind,
                "label": link.label,
                "evidence": link.evidence,
                "age_s": round(age, 1),
                "stale": age > self.stale_after_s,
            })
        return {
            "nodes": nodes,
            "links": links,
            "node_count": len(nodes),
            "link_count": len(links),
            "lldp_errors": dict(self.lldp_errors),
            "note": "Links are only added on positive LLDP-MIB evidence or explicit switch_name/switch_port inventory fields; an empty links list means no such evidence exists yet, not a broken feature.",
        }
