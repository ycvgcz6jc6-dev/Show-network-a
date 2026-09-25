"""Central cross-protocol device model for Show Network.

This layer never invents identity. It consolidates records only when the
inventory already provides a stable unique_id, or when observations share an
explicit IP/interface tuple. Conflicts are exposed instead of guessed away.
"""
from __future__ import annotations
from collections import defaultdict
from time import time
from typing import Any

class DeviceModel:
    def build(self, inventory: list[dict], topology: dict | None = None) -> dict:
        topology = topology or {}
        nodes = topology.get("nodes", []) or []
        links = topology.get("links", []) or []
        by_ip: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in inventory:
            if row.get("ip"):
                by_ip[(str(row.get("interface") or ""), str(row["ip"]))].append(row)

        devices = []
        conflicts = []
        for row in inventory:
            uid = str(row.get("unique_id") or "")
            if not uid:
                continue
            ip = row.get("ip")
            matching_nodes = [n for n in nodes if n.get("id") == uid or (ip and n.get("ip") == ip and (not row.get("interface") or not n.get("interface") or n.get("interface") == row.get("interface")))]
            matching_links = [l for l in links if l.get("source") == uid or l.get("target") == uid or
                              any(n.get("id") in (l.get("source"), l.get("target")) for n in matching_nodes)]
            evidence_sources = sorted({str(e.get("source")) for e in row.get("evidence", []) if e.get("source")})
            physical_links = []
            for link in matching_links:
                if link.get("protocol") not in {"LLDP", "LLDP/inventory"}:
                    continue
                peer = link.get("target") if link.get("source") == uid else link.get("source")
                local_port = link.get("source_port") if link.get("source") == uid else link.get("target_port")
                peer_port = link.get("target_port") if link.get("source") == uid else link.get("source_port")
                physical_links.append({
                    "peer_id": peer, "local_port": local_port, "peer_port": peer_port,
                    "vlan": link.get("vlan"), "link_speed_mbps": link.get("link_speed_mbps"),
                    "protocol": link.get("protocol"), "confidence": link.get("confidence"),
                    "evidence": link.get("evidence"), "health": link.get("health"),
                })
            devices.append({
                "id": uid,
                "name": row.get("display_name") or row.get("hostname") or row.get("model") or uid,
                "ip": ip, "ipv6": row.get("ipv6"), "mac": row.get("mac"), "serial": row.get("serial"),
                "manufacturer": row.get("display_manufacturer") or row.get("manufacturer"),
                "model": row.get("display_model") or row.get("model"), "firmware": row.get("firmware"),
                "category": row.get("category"), "location": row.get("custom_location"), "role": row.get("custom_role"),
                "interface": row.get("interface"), "vlan": row.get("vlan"),
                "switch_name": row.get("switch_name"), "switch_port": row.get("switch_port"),
                "link_speed_mbps": row.get("link_speed_mbps"),
                "protocols": sorted(set(row.get("protocols") or [])), "sources": sorted(set(row.get("sources") or [])),
                "evidence_sources": evidence_sources, "confidence": row.get("confidence"),
                "confidence_score": row.get("confidence_score", 0.0), "first_seen": row.get("first_seen"), "last_seen": row.get("last_seen"),
                "topology_nodes": [n.get("id") for n in matching_nodes], "topology_links": len(matching_links),
                "physical_links": physical_links,
                "physical_path": {
                    "interface": row.get("interface"), "vlan": row.get("vlan"),
                    "switch": row.get("switch_name"), "port": row.get("switch_port"),
                    "link_speed_mbps": row.get("link_speed_mbps"),
                },
                "monitor_mode": row.get("monitor_mode", "auto"),
            })
        for (interface, ip), rows in by_ip.items():
            ids = sorted({str(r.get("unique_id")) for r in rows if r.get("unique_id")})
            stable = [i for i in ids if i.startswith("mac:") or i.startswith("serial:")]
            if len(stable) > 1:
                conflicts.append({"type":"identity_conflict", "ip":ip, "interface":interface or None, "device_ids":stable,
                                  "message":"Plusieurs identités stables partagent la même IP sur la même interface observée"})
        return {"generated_at": round(time(), 3), "count": len(devices), "devices": devices,
                "conflicts": conflicts, "conflict_count": len(conflicts)}

    def correlate_event(self, event: dict, model: dict) -> dict:
        """Attach device ids only from explicit values present in event evidence."""
        data = event.get("data") or {}
        devices = model.get("devices", []) or []
        tokens = {str(v).strip().lower() for k, v in data.items()
                  if k in {"source", "host", "ip", "key", "switch", "name", "uid", "device_id", "remote_system", "mac", "serial"}
                  and v not in (None, "")}
        related = []
        for d in devices:
            facts = {str(d.get(k)).strip().lower() for k in ("id", "ip", "mac", "name", "switch_name") if d.get(k)}
            facts.update(str(x).strip().lower() for x in (d.get("sources") or []) if x)
            if tokens & facts:
                related.append(d.get("id"))
        out = dict(event)
        out["related_device_ids"] = sorted({x for x in related if x})
        return out

    def correlate_flight_recorder(self, recorder: dict, model: dict) -> dict:
        """Correlate timeline/incidents with the central model without fuzzy guesses."""
        if not recorder:
            return {}
        out = dict(recorder)
        out["timeline"] = [self.correlate_event(e, model) for e in recorder.get("timeline", [])]
        incidents = []
        for incident in recorder.get("incidents", []):
            item = self.correlate_event(incident, model)
            related = [self.correlate_event(e, model) for e in incident.get("related_events", [])]
            item["related_events"] = related
            ids = set(item.get("related_device_ids", []))
            for e in related:
                ids.update(e.get("related_device_ids", []))
            item["related_device_ids"] = sorted(ids)
            incidents.append(item)
        out["incidents"] = incidents
        out["last_incident"] = incidents[-1] if incidents else None
        return out
    def attach_event_history(self, model: dict, events: list[dict]) -> dict:
        """Attach recent evidence-linked lifecycle/incident history to each device.

        The archive is bounded, so first_seen is inventory lifetime while
        history_first_event is only the oldest event still present in memory.
        """
        if not model:
            return {}
        out = dict(model)
        correlated = [self.correlate_event(e, model) for e in (events or [])]
        interesting = {
            "device_appeared", "device_disappeared", "device_moved",
            "device_lost", "device_recovered", "telemetry_stale",
            "telemetry_recovered", "clock_master_change", "grandmaster_change",
            "clock_lost", "clock_recovered", "bandwidth_warning",
            "bandwidth_critical", "rx_errors_increased", "tx_errors_increased",
            "error_change", "activity_change",
        }
        devices=[]
        for dev in model.get("devices", []) or []:
            item=dict(dev); did=dev.get("id")
            history=[]
            for ev in correlated:
                if did not in (ev.get("related_device_ids") or []):
                    continue
                if ev.get("event") not in interesting and ev.get("kind") not in {"dante","ptp","lldp","switch","amplifier","projector"}:
                    continue
                history.append({
                    "ts": ev.get("ts"), "kind": ev.get("kind"),
                    "event": ev.get("event"), "data": ev.get("data") or {},
                })
            history.sort(key=lambda x: str(x.get("ts") or ""))
            item["event_history"] = history[-50:]
            item["event_history_count"] = len(history)
            item["history_first_event"] = history[0].get("ts") if history else None
            item["history_last_event"] = history[-1].get("ts") if history else None
            devices.append(item)
        out["devices"] = devices
        out["history_event_count"] = sum(d.get("event_history_count",0) for d in devices)
        return out

