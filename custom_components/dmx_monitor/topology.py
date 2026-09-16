"""Evidence-based Show Network topology and health model.

Topology is descriptive/read-only: links are created only from explicit evidence
such as LLDP, switch-port inventory, or a trusted device identity.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from time import time
from typing import Any

@dataclass
class TopologyNode:
    id: str
    label: str
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    ip: str | None = None
    mac: str | None = None
    vlan: int | None = None
    confidence: float = 0.0
    source: str = "inventory"
    protocols: list[str] = field(default_factory=list)
    health: str = "unknown"
    last_seen: float = 0.0

@dataclass
class TopologyLink:
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    vlan: int | None = None
    link_speed_mbps: int | None = None
    protocol: str | None = None
    confidence: float = 0.0
    evidence: str = ""
    health: str = "unknown"
    last_seen: float = 0.0

class ShowTopology:
    def __init__(self, stale_after_s: float = 120.0):
        self.nodes: dict[str, TopologyNode] = {}
        self.links: dict[tuple[str, str, str | None, str | None], TopologyLink] = {}
        self.stale_after_s = float(stale_after_s)

    def upsert_node(self, node_id: str, **kwargs: Any) -> TopologyNode:
        now = time()
        node = self.nodes.get(node_id)
        if node is None:
            node = TopologyNode(id=node_id, label=kwargs.get("label") or node_id, last_seen=now)
            self.nodes[node_id] = node
        for key in ("label", "manufacturer", "model", "category", "ip", "mac", "vlan", "confidence", "source", "health"):
            if kwargs.get(key) is not None:
                setattr(node, key, kwargs[key])
        protocols = kwargs.get("protocols")
        if protocols:
            node.protocols = sorted(set(node.protocols).union(str(p) for p in protocols))
        node.last_seen = now
        return node

    def observe_protocol(self, node_id: str, protocol: str, **kwargs: Any) -> TopologyNode:
        node = self.upsert_node(node_id, **kwargs)
        if protocol and protocol not in node.protocols:
            node.protocols.append(protocol)
            node.protocols.sort()
        return node

    def observe_link(self, source: str, target: str, *, source_port=None, target_port=None,
                     vlan=None, link_speed_mbps=None, protocol=None, confidence=1.0,
                     evidence="observed") -> TopologyLink:
        self.upsert_node(source, label=source)
        self.upsert_node(target, label=target)
        key = (source, target, source_port, target_port)
        now = time()
        link = self.links.get(key)
        if link is None:
            link = TopologyLink(source, target, source_port, target_port, vlan,
                                link_speed_mbps, protocol, float(confidence), evidence,
                                "up", now)
            self.links[key] = link
        else:
            for name, value in (("vlan", vlan), ("link_speed_mbps", link_speed_mbps),
                                ("protocol", protocol)):
                if value is not None:
                    setattr(link, name, value)
            link.confidence = max(link.confidence, float(confidence))
            link.evidence = evidence or link.evidence
            link.health = "up"
            link.last_seen = now
        return link

    def ingest_inventory(self, records: list[dict]):
        for record in records:
            uid = record.get("unique_id") or record.get("serial") or record.get("mac") or record.get("ip")
            if not uid:
                continue
            self.upsert_node(uid,
                label=record.get("hostname") or record.get("model") or uid,
                manufacturer=record.get("manufacturer"), model=record.get("model"),
                category=record.get("category"), ip=record.get("ip"), mac=record.get("mac"),
                vlan=record.get("vlan"), confidence=float(record.get("confidence_score") or 0),
                source="device_inventory", protocols=record.get("protocols") or [])
            sw = record.get("switch_name")
            port = record.get("switch_port")
            if sw:
                self.observe_link(sw, uid, source_port=port,
                    vlan=record.get("vlan"), link_speed_mbps=record.get("link_speed_mbps"),
                    protocol="LLDP/inventory", confidence=.95 if port else .75,
                    evidence="switch_port + device inventory")

    def refresh_health(self, now: float | None = None) -> dict[str, int]:
        now = time() if now is None else now
        counts = {"up": 0, "stale": 0, "unknown": 0}
        for node in self.nodes.values():
            if node.health != "error":
                node.health = "up" if now - node.last_seen <= self.stale_after_s else "stale"
            counts[node.health] = counts.get(node.health, 0) + 1
        for link in self.links.values():
            link.health = "up" if now - link.last_seen <= self.stale_after_s else "stale"
        return counts

    def snapshot(self) -> dict:
        self.refresh_health()
        return {"nodes": [asdict(n) for n in self.nodes.values()],
                "links": [asdict(l) for l in self.links.values()]}
