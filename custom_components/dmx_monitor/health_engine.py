"""Cross-protocol health correlation for Show Network.

The engine is deliberately evidence-based: it reports observations and checks,
never a guessed root cause. It consumes already-normalized coordinator data and
can therefore be unit-tested without network access or Home Assistant.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import time
from typing import Any

@dataclass(frozen=True)
class HealthCheck:
    key: str
    status: str  # ok | warning | error | info
    title: str
    detail: str
    evidence: dict[str, Any]

class ShowNetworkHealthEngine:
    """Build a compact operator-oriented diagnostic from live snapshots."""

    def run(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        checks: list[HealthCheck] = []
        self._interfaces(snapshot, checks)
        self._dmx(snapshot, checks)
        self._topology(snapshot, checks)
        self._ptp(snapshot, checks)
        self._archive(snapshot, checks)
        self._host(snapshot, checks)
        counts = {name: sum(c.status == name for c in checks) for name in ("ok", "warning", "error", "info")}
        overall = "error" if counts["error"] else "warning" if counts["warning"] else "ok"
        return {
            "generated_at_epoch": round(time(), 3),
            "overall": overall,
            "checks_total": len(checks),
            "counts": counts,
            "checks": [asdict(c) for c in checks],
        }

    @staticmethod
    def _add(out, key, status, title, detail, **evidence):
        out.append(HealthCheck(key, status, title, detail, evidence))

    def _interfaces(self, s, out):
        interfaces = s.get("network_interfaces") or []
        if isinstance(interfaces, dict):
            interfaces = interfaces.get("interfaces") or interfaces.get("items") or []
        self._add(out, "interfaces.present", "ok" if interfaces else "warning",
                  "Interfaces réseau", f"{len(interfaces)} interface(s) publiée(s)" if interfaces else "Aucune interface réseau publiée",
                  count=len(interfaces))
        nh = s.get("network_health") or {}
        stale = int(nh.get("interfaces_stale") or 0)
        up = int(nh.get("interfaces_up") or 0)
        if stale:
            self._add(out, "interfaces.stale", "warning", "Télémétrie réseau vieillissante",
                      f"{stale} interface(s) sans observation récente", stale=stale, up=up)
        elif up:
            self._add(out, "interfaces.telemetry", "ok", "Télémétrie réseau", f"{up} interface(s) active(s)", up=up)

    def _dmx(self, s, out):
        rows = s.get("dmx_universes") or s.get("universes") or []
        if isinstance(rows, dict): rows = rows.get("universes") or rows.get("items") or []
        if not rows:
            self._add(out, "dmx.activity", "info", "DMX réseau", "Aucun univers DMX actif observé", universes=0)
            return
        groups: dict[tuple[str, int], set[str]] = {}
        lossy = []
        for r in rows:
            if not isinstance(r, dict): continue
            proto = str(r.get("protocol") or "unknown")
            try: uni = int(r.get("universe"))
            except (TypeError, ValueError): continue
            groups.setdefault((proto, uni), set()).add(str(r.get("source") or "unknown"))
            if float(r.get("sequence_loss_pct") or 0) >= 1.0:
                lossy.append({"protocol": proto, "universe": uni, "source": r.get("source"), "loss_pct": r.get("sequence_loss_pct")})
        multi = [{"protocol": p, "universe": u, "sources": sorted(src)} for (p,u),src in groups.items() if len(src) > 1]
        self._add(out, "dmx.activity", "ok", "DMX réseau", f"{len(groups)} univers/protocole observé(s)", universes=len(groups))
        if multi:
            self._add(out, "dmx.multiple_sources", "warning", "Sources DMX multiples",
                      f"{len(multi)} univers/protocole ont plusieurs sources; vérifier si c'est attendu", universes=multi[:20])
        if lossy:
            self._add(out, "dmx.sequence_loss", "warning", "Pertes de séquence sACN",
                      f"{len(lossy)} source(s) dépassent 1 % de perte observée", sources=lossy[:20])

    def _topology(self, s, out):
        topo = s.get("topology") or {}
        nodes, links = topo.get("nodes") or [], topo.get("links") or []
        stale_nodes = [n for n in nodes if n.get("health") == "stale"]
        stale_links = [l for l in links if l.get("health") == "stale"]
        if nodes:
            self._add(out, "topology.inventory", "ok", "Topologie", f"{len(nodes)} nœud(s), {len(links)} lien(s)", nodes=len(nodes), links=len(links))
        if stale_nodes or stale_links:
            self._add(out, "topology.stale", "warning", "Topologie vieillissante",
                      f"{len(stale_nodes)} nœud(s) et {len(stale_links)} lien(s) sont stale",
                      stale_nodes=[n.get("label") or n.get("id") for n in stale_nodes[:20]], stale_links=len(stale_links))

    def _ptp(self, s, out):
        sources = int(s.get("ptp_sources") or 0)
        packets = int(s.get("ptp_packets") or 0)
        if packets or sources:
            self._add(out, "ptp.activity", "ok", "PTP", f"{sources} source(s), {packets} paquet(s) observé(s)", sources=sources, packets=packets)
        # Only report explicit state supplied by a monitor; never infer a grandmaster.
        ptp = s.get("ptp") or s.get("ptp_health") or {}
        if isinstance(ptp, dict):
            state = str(ptp.get("health") or ptp.get("status") or "").lower()
            if state in {"warning", "degraded", "error", "fault"}:
                self._add(out, "ptp.explicit_health", "error" if state in {"error","fault"} else "warning",
                          "État PTP signalé", f"Le moniteur PTP publie l'état « {state} »", state=state)

    def _archive(self, s, out):
        a = s.get("archive") or {}
        if not isinstance(a, dict) or not a: return
        failures = int(a.get("dropped_events") or 0) + int(a.get("write_errors") or 0) + int(a.get("rotate_errors") or 0)
        if a.get("over_limit") or failures:
            self._add(out, "archive.health", "warning", "Journal / Flight Recorder",
                      "Le journal signale une limite ou des erreurs d'écriture", over_limit=bool(a.get("over_limit")), failures=failures)
        elif a.get("storage_ready") is True:
            self._add(out, "archive.health", "ok", "Journal / Flight Recorder", "Stockage du journal disponible", bytes=a.get("bytes_total"))

    def _host(self, s, out):
        h = s.get("host_metrics") or {}
        cpu, mem = h.get("cpu_percent"), h.get("memory_percent")
        high = (isinstance(cpu, (int,float)) and cpu >= 90) or (isinstance(mem, (int,float)) and mem >= 90)
        if cpu is not None or mem is not None:
            self._add(out, "host.capacity", "warning" if high else "ok", "Serveur Home Assistant",
                      f"CPU {cpu if cpu is not None else '—'} % · RAM {mem if mem is not None else '—'} %", cpu_percent=cpu, memory_percent=mem)
