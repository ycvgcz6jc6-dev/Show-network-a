"""Passive grandMA3 remote/session inventory helpers."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from time import monotonic, time
from urllib.parse import urlunparse

MA_WEB_REMOTE_PORT = 8080
MA_OSC_DEFAULT_PORT = 8000
_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # RFC 6455 magic string


async def _probe_web_remote_handshake(host: str, port: int, timeout: float) -> bool:
    """RFC 6455 WebSocket handshake to the grandMA3 Web Remote's own
    endpoint (ws://host:port/?ma=1), stopping the instant the server's
    unconditional post-connect reply is read.

    Verified directly against a real Web Remote page's own client code
    (interface.js: `serverURI = "ws://" + window.location.host + "/?ma=1"`,
    and `SocketOnMessage` checking `(...).status != "server ready"`
    *before* handling anything session-related). That "server ready"
    JSON reply is sent by the console the instant the socket opens --
    before any login, before any `remoteState` request, before any
    `requestVideo` -- so reading it is a status check, not a session
    interaction. This function stops there: it never sends a
    `requestType` message of any kind (no "remoteState", no
    "requestVideo"), matching "Aucun join implicite" for MA-Net3/Web
    Remote alike.

    Stronger evidence than a bare TCP connect (the previous
    implementation): confirms an actual grandMA3 Web Remote answered,
    not merely that *some* process is listening on the port.
    """
    reader = writer = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET /?ma=1 HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        ).encode("ascii")
        writer.write(request)
        await asyncio.wait_for(writer.drain(), timeout=timeout)

        header_bytes = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=timeout)
        header_text = header_bytes.decode("iso-8859-1", errors="replace")
        status_line = header_text.split("\r\n", 1)[0]
        if " 101 " not in f" {status_line} ":
            return False
        accept_value = None
        for line in header_text.split("\r\n"):
            if line.lower().startswith("sec-websocket-accept:"):
                accept_value = line.split(":", 1)[1].strip()
                break
        if accept_value is None:
            return False
        expected = base64.b64encode(hashlib.sha1((key + _WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
        if accept_value != expected:
            return False  # answered HTTP, but not a genuine WebSocket peer

        frame_head = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
        opcode = frame_head[0] & 0x0F
        masked = bool(frame_head[1] & 0x80)
        length = frame_head[1] & 0x7F
        if length == 126:
            length = int.from_bytes(await asyncio.wait_for(reader.readexactly(2), timeout=timeout), "big")
        elif length == 127:
            length = int.from_bytes(await asyncio.wait_for(reader.readexactly(8), timeout=timeout), "big")
        length = min(length, 65536)  # a status reply is small; never read an unbounded amount
        mask_key = await asyncio.wait_for(reader.readexactly(4), timeout=timeout) if masked else None
        payload = await asyncio.wait_for(reader.readexactly(length), timeout=timeout)
        if mask_key:  # servers must not mask per RFC 6455, but decode defensively if one does
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        if opcode != 0x1:  # not a text frame
            return False

        message = json.loads(payload.decode("utf-8"))
        return isinstance(message, dict) and message.get("status") == "server ready"
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, UnicodeDecodeError, ValueError):
        return False
    finally:
        if writer is not None:
            writer.close()  # fire-and-forget close, same reasoning as the
            # earlier TCP-only probe: this is a status check, not a real
            # session, so no close handshake is awaited.


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
        self._web_remote_probed_once = False

    async def async_probe_web_remote(self, timeout: float = 1.5) -> None:
        """Real RFC 6455 WebSocket handshake to each station's Web Remote
        (see _probe_web_remote_handshake's own docstring for the exact
        wire evidence this is grounded in) -- confirms an actual grandMA3
        Web Remote answered, not just that some process is listening on
        the port. Updates each station's `web_remote` field to
        "available"/"unavailable" (rapport maître S113: "Web Remote:
        UNKNOWN / AVAILABLE / UNAVAILABLE"). Before this ever runs, the
        field stays "unknown" -- audit-confirmed gap: "Web Remote
        affichés mais disponibilité non prouvée" -- rather than the URL
        being presented as if verified.
        """
        async def _probe_one(station: MAStation) -> None:
            ok = await _probe_web_remote_handshake(station.ip, MA_WEB_REMOTE_PORT, timeout)
            station.web_remote = "available" if ok else "unavailable"

        if not self.stations:
            return
        self._web_remote_probed_once = True
        await asyncio.gather(*(_probe_one(s) for s in self.stations.values()), return_exceptions=True)

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
        # web_remote is intentionally NOT touched here: it starts at the
        # dataclass default "unknown" for a newly created station and is
        # only ever updated by async_probe_web_remote()'s real TCP-connect
        # check. Resetting it on every packet (this method fires on every
        # observed MA-Net3 packet, i.e. constantly for an active station)
        # would erase that probe result almost immediately.

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
                "web_remote_probe": "websocket_handshake" if self._web_remote_probed_once else False,
                "classification_policy": "payload_marker_only_unknown_until_evidence",
                "freshness_policy": "packet_receive_time_not_coordinator_replay",
                "osc_commands_sent": False,
            },
        }
