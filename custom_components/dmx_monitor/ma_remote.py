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

    def snapshot(self) -> dict:
        d = asdict(self)
        d["web_remote_url"] = self.web_remote_url
        d["age_s"] = round(max(0.0, monotonic() - self.last_seen), 1) if self.last_seen is not None else None
        d["state"] = "LIVE" if self.ma_net3_active else "STALE"
        return d


class MARemoteInventory:
    """Correlates passive MA-Net3 source addresses and multicast session indexes."""
    def __init__(self):
        self.stations: dict[str, MAStation] = {}

    @staticmethod
    def _classify(hints):
        text = " ".join(str(x) for x in (hints or [])).lower()
        checks = (
            ("grandMA3 onPC", ("onpc", "on pc")),
            ("grandMA3 xPort Node", ("xport node", "xport")),
            ("grandMA3 Processing Unit", ("processing unit", "grandma3 pu")),
            ("MA NPU", (" npu", "npu ")),
            ("MA RPU", (" rpu", "rpu ")),
            ("grandMA3 Node", ("grandma3 node", "ma3 node")),
            ("grandMA3 Console", ("grandma3 full-size", "grandma3 light", "grandma3 compact", "grandma3 console")),
        )
        for kind, markers in checks:
            marker = next((m for m in markers if m in text), None)
            if marker:
                return kind, marker
        return None, None

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

        kind, evidence = self._classify(identity_hints)
        if kind:
            station.device_type = kind
            station.model = kind
            station.classification_evidence = f"payload marker: {evidence}"
            station.name = f"{kind} {source_ip}"
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
            sessions.append({
                "session_index": idx,
                "member_count": len(members),
                "members": [m["ip"] for m in members],
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
            "sessions_note": "Session index inferred only from observed MA-Net3 session multicast groups; name/location/master remain unknown without payload evidence.",
            "web_remote_port": MA_WEB_REMOTE_PORT,
            "web_remote_candidates": [],
            "osc": {"default_port": MA_OSC_DEFAULT_PORT, "transport": "UDP/TCP", "observed": False, "control_enabled": False},
            "device_types": {kind: sum(1 for x in rows if x.get("device_type") == kind) for kind in sorted({x.get("device_type") for x in rows if x.get("device_type")})},
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
