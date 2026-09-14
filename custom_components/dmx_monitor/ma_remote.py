"""Passive grandMA3 remote/session inventory helpers.

No MA session join and no MA control is performed.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import monotonic
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
    version: str | None = None
    showfile: str | None = None
    uptime: str | None = None
    ma_net3_active: bool = False
    web_remote: str = "unknown"
    last_seen: float | None = None
    packets: int = 0

    @property
    def web_remote_url(self) -> str:
        return urlunparse(("http", f"{self.ip}:{MA_WEB_REMOTE_PORT}", "", "", "", ""))

    def snapshot(self) -> dict:
        d = asdict(self)
        d["web_remote_url"] = self.web_remote_url
        if self.last_seen is not None:
            d["age_s"] = round(max(0.0, monotonic() - self.last_seen), 1)
        else:
            d["age_s"] = None
        d["state"] = "LIVE" if self.ma_net3_active else "STALE"
        return d

class MARemoteInventory:
    """Correlates passive MA-Net3 sources into station records."""
    def __init__(self):
        self.stations: dict[str, MAStation] = {}

    def observe(self, source_ip: str, group: str, packet_count: int = 1):
        station = self.stations.get(source_ip)
        if station is None:
            station = MAStation(name=f"MA station non classifiée {source_ip}", ip=source_ip)
            self.stations[source_ip] = station
        station.last_seen = monotonic()
        station.packets += packet_count
        station.ma_net3_active = True
        station.web_remote = "not_probed"

    def snapshot(self) -> dict:
        rows = [s.snapshot() for s in self.stations.values()]
        rows.sort(key=lambda x: (x.get("state") != "LIVE", x["ip"]))
        now = monotonic()
        for station in self.stations.values():
            if station.last_seen is not None and now - station.last_seen > 15:
                station.ma_net3_active = False
        rows = [s.snapshot() for s in self.stations.values()]
        rows.sort(key=lambda x: x["ip"])
        return {
            "stations": rows,
            "station_count": len(rows),
            "live_stations": sum(1 for x in rows if x["state"] == "LIVE"),
            "sessions": [],
            "session_count": 0,
            "sessions_note": "Session index/name require MA session metadata; passive listener does not join sessions.",
            "web_remote_port": MA_WEB_REMOTE_PORT,
            "web_remote_candidates": [],
            "osc": {"default_port": MA_OSC_DEFAULT_PORT, "transport": "UDP/TCP", "observed": False, "control_enabled": False},
            "diagnostics": {
                "receive_only": True,
                "session_join": False,
                "ma_commands_sent": False,
                "web_remote_probe": False,
                "classification_policy": "unknown_until_evidence",
                "osc_commands_sent": False,
            },
        }
