"""Passive grandMA3 remote/session inventory helpers."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import monotonic, time
from urllib.parse import urlunparse

MA_WEB_REMOTE_PORT = 8080
MA_OSC_DEFAULT_PORT = 8000


@dataclass
class MAStation:
    name: str
    ip: str
    session_index: int | None = None
    session_name: str | None = None
    model: str | None = None
    device_type: str | None = None
    category: str | None = None  # "console" | "processing_unit" | "node" | "software"
    classification_evidence: str | None = None
    version: str | None = None
    showfile: str | None = None
    uptime: str | None = None
    ma_net3_active: bool = False
    web_remote: str = "unknown"
    last_seen: float | None = None  # monotonic receive time when available
    last_packet_epoch: float | None = None
    packets: int = 0
    session_evidence: str | None = None

    @property
    def web_remote_url(self) -> str:
        return urlunparse(("http", f"{self.ip}:{MA_WEB_REMOTE_PORT}", "", "", "", ""))

    @property
    def proxy_url(self) -> str:
        """HA-hosted HTTPS/WSS front door for this console's Web Remote (see
        ma3_web_remote_view.py). Unlike web_remote_url, this one keeps
        working when Home Assistant is reached over HTTPS (Nabu Casa etc.)."""
        return f"/api/dmx_monitor/ma_remote/{self.ip}/"

    def snapshot(self) -> dict:
        d = asdict(self)
        d["web_remote_url"] = self.web_remote_url
        d["proxy_url"] = self.proxy_url
        d["age_s"] = round(max(0.0, monotonic() - self.last_seen), 1) if self.last_seen is not None else None
        d["state"] = "LIVE" if self.ma_net3_active else "STALE"
        return d


class MARemoteInventory:
    """Correlates passive MA-Net3 source addresses and multicast session indexes."""
    def __init__(self):
        self.stations: dict[str, MAStation] = {}

    @staticmethod
    def _classify(hints):
        """Classify a grandMA3 device from MA-Net3 identity markers.

        Returns (category, model, evidence_marker) where category is one of
        "console", "processing_unit", "node", "software", or (None, None,
        None) if nothing matched. Model names come from MA Lighting's
        published product line (verified against malighting.com), not from
        a captured packet -- extend the marker lists if real identity_hints
        text differs. There is no MA Lighting product called "RPU"; the
        closest real product is the "grandMA3 replay unit" (a playback-only
        *console* variant), classified accordingly here.
        """
        text = " ".join(str(x) for x in (hints or [])).lower()
        checks = (
            ("software", "grandMA3 onPC", ("onpc", "on pc", "on-pc")),
            ("processing_unit", "grandMA3 processing unit XL (NPU XL)", ("processing unit xl", "npu xl")),
            ("processing_unit", "grandMA3 processing unit L (NPU L)", ("processing unit l", "npu l")),
            ("processing_unit", "grandMA3 processing unit M (NPU M)", ("processing unit m", "npu m")),
            ("processing_unit", "grandMA3 processing unit (NPU)", ("processing unit", "npu")),
            ("node", "grandMA3 xPort Node", ("xport node", "xport")),
            ("node", "grandMA3 I/O Node", ("i/o node", "io node")),
            ("node", "grandMA3 Node", ("grandma3 node", "ma3 node", "ma-net3 node")),
            ("console", "grandMA3 Replay Unit", ("replay unit",)),
            ("console", "grandMA3 Extension", ("extension console", "grandma3 extension")),
            ("console", "grandMA3 Compact XT", ("compact xt",)),
            ("console", "grandMA3 Compact", ("grandma3 compact",)),
            ("console", "grandMA3 Light CRV", ("light crv",)),
            ("console", "grandMA3 Light", ("grandma3 light",)),
            ("console", "grandMA3 Full-Size CRV", ("full-size crv", "full size crv")),
            ("console", "grandMA3 Full-Size", ("grandma3 full-size", "full-size console", "full size console")),
            ("console", "grandMA3 Console", ("grandma3 console",)),
        )
        for category, kind, markers in checks:
            marker = next((m for m in markers if m in text), None)
            if marker:
                return category, kind, marker
        # Fallback confirmed necessary by a real capture: a grandMA3 Node
        # whose operator gave it a site-specific custom label ("Node-ma-
        # salle-b" -- "Node" + a room name) matched none of the strict
        # product-name markers above, since it is not MA Lighting's own
        # product-name text at all. A standalone, word-boundary match on
        # a generic category word is weaker evidence than a confirmed
        # product name, so it is returned with distinct, honestly-labeled
        # evidence rather than silently treated the same way.
        import re as _re
        for word, category in (("node", "node"), ("console", "console"), ("npu", "processing_unit")):
            if _re.search(r"\b" + word + r"\b", text):
                return category, None, f"generic word match: {word!r} in custom device label (not a confirmed product name)"
        return None, None, None

    def observe(self, source_ip: str, group: str, packet_count: int = 1,
                session_index: int | None = None, identity_hints=None,
                observed_at: float | None = None, packet_epoch: float | None = None):
        station = self.stations.get(source_ip)
        if station is None:
            station = MAStation(name=f"MA station non classifiée {source_ip}", ip=source_ip)
            self.stations[source_ip] = station

        receive_time = observed_at if observed_at is not None else monotonic()
        # Coordinator may replay cached observations on each refresh.  Never
        # turn such replay into fresh network evidence or duplicate packets.
        is_new = station.last_seen is None or receive_time > station.last_seen
        if is_new:
            station.last_seen = receive_time
            station.last_packet_epoch = packet_epoch if packet_epoch is not None else time()
            station.packets += packet_count
        station.ma_net3_active = station.last_seen is not None and monotonic() - station.last_seen <= 15.0
        station.web_remote = "not_probed"

        category, kind, evidence = self._classify(identity_hints)
        if kind:
            station.device_type = kind
            station.category = category
            station.model = kind
            station.classification_evidence = f"payload marker: {evidence}"
            station.name = f"{kind} {source_ip}"
        elif category:
            # Fallback case: category inferred from a generic word in a
            # custom device label, no confirmed product name available.
            station.device_type = f"{category} (nom personnalisé, produit non confirmé)"
            station.category = category
            station.classification_evidence = evidence
            station.name = f"{category} {source_ip}"
        if session_index is not None:
            station.session_index = int(session_index)
            station.session_evidence = "multicast_group"

    def snapshot(self) -> dict:
        now = monotonic()
        for station in self.stations.values():
            if station.last_seen is not None and now - station.last_seen > 15.0:
                station.ma_net3_active = False
        rows = [s.snapshot() for s in self.stations.values()]
        rows.sort(key=lambda x: x["ip"])
        sessions = []
        for idx in sorted({s.session_index for s in self.stations.values() if s.session_index is not None}):
            members = [s.snapshot() for s in self.stations.values() if s.session_index == idx]
            live_members = [m for m in members if m.get("state") == "LIVE"]
            sessions.append({
                "session_index": idx,
                "member_count": len(members),
                "live_member_count": len(live_members),
                "members": [m["ip"] for m in members],
                "live_members": [m["ip"] for m in live_members],
                "state": "LIVE" if live_members else "STALE",
                "name": None,
                "location": None,
                "master": None,
                "evidence": "MA-Net3 multicast group",
            })
        unknown = sum(1 for x in rows if not x.get("device_type"))
        return {
            "stations": rows,
            "station_count": len(rows),
            "live_stations": sum(1 for x in rows if x["state"] == "LIVE"),
            "classified_stations": len(rows) - unknown,
            "unclassified_stations": unknown,
            "sessions": sessions,
            "session_count": len(sessions),
            "active_session_count": sum(1 for x in sessions if x.get("state") == "LIVE"),
            "sessions_note": "Session index inferred only from observed MA-Net3 session multicast groups; name/location/master remain unknown without payload evidence.",
            "web_remote_port": MA_WEB_REMOTE_PORT,
            "web_remote_candidates": [],
            "osc": {"default_port": MA_OSC_DEFAULT_PORT, "transport": "UDP/TCP", "observed": False, "control_enabled": False},
            "device_types": {kind: sum(1 for x in rows if x.get("device_type") == kind) for kind in sorted({x.get("device_type") for x in rows if x.get("device_type")})},
            "categories": {cat: sum(1 for x in rows if x.get("category") == cat) for cat in sorted({x.get("category") for x in rows if x.get("category")})},
            "diagnostics": {
                "receive_only": True,
                "session_join": False,
                "ma_commands_sent": False,
                "web_remote_probe": False,
                "classification_policy": "payload_marker_only_unknown_until_evidence",
                "freshness_policy": "packet_receive_time_not_coordinator_replay",
                "osc_commands_sent": False,
            },
        }
