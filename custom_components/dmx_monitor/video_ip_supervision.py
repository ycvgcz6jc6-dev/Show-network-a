"""Passive video-over-IP supervision kernel.

Phase 10 is intentionally supervision-only:
- no Home Assistant entities are created here;
- no sockets are opened to media endpoints;
- no streams are subscribed to or controlled;
- observations come from already-available passive discovery evidence.

The snapshot is consumed directly by the Show Network panel through an
authenticated Home Assistant websocket command.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import socket
import time
from typing import Any
from urllib.parse import quote

_VIDEO_MARKERS = (
    "video", "camera", "encoder", "decoder", "stream", "ndi", "rtsp",
    "srt", "h264", "h.264", "h265", "h.265", "hevc", "av-over-ip",
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _haystack(row: dict[str, Any]) -> str:
    props = row.get("properties") or {}
    parts = [row.get("service_type"), row.get("name"), row.get("host"), row.get("vendor")]
    for key, value in props.items():
        parts.extend((key, value))
    return " ".join(_text(x).lower() for x in parts if x is not None)


def _first_address(row: dict[str, Any]) -> str | None:
    addresses = row.get("addresses") or []
    if addresses:
        return _text(addresses[0]) or None
    host = _text(row.get("host"))
    return host or None


def _property_path(props: dict[str, Any]) -> str | None:
    for key in ("path", "url", "uri", "stream", "stream_path"):
        value = _text(props.get(key))
        if value:
            return value
    return None


def _route_source_for_ip(host: str) -> str | None:
    """Return the local IPv4 address the OS would route toward host.

    UDP connect() selects a route/source address without sending a datagram.
    This lets supervision honor a selected show-network NIC without active
    media probing.
    """
    try:
        ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, ValueError):
        return None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((host, 9))
        return str(sock.getsockname()[0])
    except OSError:
        return None
    finally:
        sock.close()


def _classify_mdns(row: dict[str, Any]) -> tuple[str | None, str]:
    """Return (protocol, evidence) without guessing from a bare port/IP."""
    service = _text(row.get("service_type")).lower()
    hay = _haystack(row)
    if "ndi" in hay:
        return "NDI", "explicit NDI marker in mDNS/DNS-SD observation"
    if service.startswith("_rtsp._tcp") or " rtsp" in f" {hay}":
        return "RTSP", "RTSP service/marker in mDNS/DNS-SD observation"
    if "srt" in hay:
        return "SRT", "explicit SRT marker in mDNS/DNS-SD observation"
    if service.startswith("_http._tcp") or service.startswith("_https._tcp"):
        if any(marker in hay for marker in _VIDEO_MARKERS):
            return "HTTPS" if service.startswith("_https") else "HTTP", "video marker on HTTP(S) DNS-SD service"
    return None, ""


@dataclass(slots=True)
class VideoIPEndpoint:
    key: str
    protocol: str
    name: str | None = None
    host: str | None = None
    port: int | None = None
    uri: str | None = None
    discovery: str = "passive"
    interface: str | None = None
    evidence: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def public(self, now: float, stale_after_s: float) -> dict[str, Any]:
        age = max(0.0, now - self.last_seen)
        return {
            "key": self.key,
            "protocol": self.protocol,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "uri": self.uri,
            "discovery": self.discovery,
            "interface": self.interface,
            "evidence": list(self.evidence[-8:]),
            "properties": dict(list(self.properties.items())[:24]),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "age_s": round(age, 1),
            "online": age <= stale_after_s,
            "vlc_direct": self.protocol in {"RTSP", "SRT", "HTTP", "HTTPS"} and bool(self.uri),
        }


class VideoIPSupervision:
    """In-memory passive inventory of video-over-IP endpoints."""

    def __init__(self, *, stale_after_s: float = 45.0, max_endpoints: int = 256) -> None:
        self.stale_after_s = max(5.0, float(stale_after_s))
        self.max_endpoints = max(16, int(max_endpoints))
        self.enabled = True
        self.interface = "0.0.0.0"
        self.preview_enabled = False
        self._endpoints: dict[str, VideoIPEndpoint] = {}
        self.observations = 0
        self.last_observed_at: float | None = None

    def configure(self, *, enabled: bool, interface: str | None = None, preview_enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.interface = _text(interface) or "0.0.0.0"
        self.preview_enabled = bool(preview_enabled)

    def endpoint(self, key: str) -> VideoIPEndpoint | None:
        return self._endpoints.get(str(key))

    def _interface_accepts(self, host: str | None) -> bool:
        if self.interface in {"", "0.0.0.0"}:
            return True
        if not host:
            return False
        routed = _route_source_for_ip(host)
        return routed == self.interface

    def observe_mdns(self, row: dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        protocol, evidence = _classify_mdns(row)
        if not protocol:
            return False
        host = _first_address(row)
        if not self._interface_accepts(host):
            return False
        name = _text(row.get("name")) or None
        port = int(row.get("port") or 0) or None
        service = _text(row.get("service_type")).lower()
        props = {str(k): _text(v) for k, v in (row.get("properties") or {}).items()}
        observed_at = float(row.get("observed_at") or time.time())
        path = _property_path(props)
        uri = None
        if protocol in {"RTSP", "HTTP", "HTTPS"} and host:
            scheme = protocol.lower()
            if path and "://" in path:
                uri = path
            else:
                suffix = path or ""
                if suffix and not suffix.startswith("/"):
                    suffix = "/" + quote(suffix, safe="/%?=&:+@")
                default_port = 443 if protocol == "HTTPS" else 80 if protocol == "HTTP" else 554
                port_part = f":{port}" if port and port != default_port else ""
                uri = f"{scheme}://{host}{port_part}{suffix}"
        elif protocol == "SRT" and host and port:
            uri = f"srt://{host}:{port}"
        # NDI deliberately has no synthetic URI. Opening NDI correctly requires
        # NDI SDK/plugin support; a DNS-SD observation alone is not a media URL.
        key = f"{protocol.lower()}:{host or 'unknown'}:{port or 0}:{name or service or 'endpoint'}"
        ep = self._endpoints.get(key)
        if ep is None:
            ep = VideoIPEndpoint(key=key, protocol=protocol, first_seen=observed_at)
            self._endpoints[key] = ep
        ep.protocol = protocol
        ep.name = name or ep.name
        ep.host = host or ep.host
        ep.port = port or ep.port
        ep.uri = uri or ep.uri
        ep.discovery = "mDNS/DNS-SD"
        ep.interface = (self.interface if self.interface != "0.0.0.0" else (_text(row.get("interface")) or ep.interface))
        ep.properties = props or ep.properties
        ep.last_seen = max(ep.last_seen, observed_at)
        if evidence and evidence not in ep.evidence:
            ep.evidence.append(evidence)
        if service:
            service_evidence = f"service={service}"
            if service_evidence not in ep.evidence:
                ep.evidence.append(service_evidence)
        self.observations += 1
        self.last_observed_at = observed_at
        self._trim()
        return True

    def observe_transport(
        self,
        protocol: str,
        *,
        host: str,
        port: int | None = None,
        name: str | None = None,
        uri: str | None = None,
        interface: str | None = None,
        evidence: str = "passive protocol observation",
        observed_at: float | None = None,
    ) -> None:
        """Accept evidence from future passive packet inspectors, without probing."""
        if not self.enabled:
            return
        proto = _text(protocol).upper()
        if proto not in {"NDI", "SRT", "RTSP", "HTTP", "HTTPS", "UDP"}:
            raise ValueError(f"unsupported video supervision protocol: {protocol}")
        when = float(observed_at or time.time())
        key = f"{proto.lower()}:{host}:{int(port or 0)}:{name or 'endpoint'}"
        ep = self._endpoints.get(key) or VideoIPEndpoint(key=key, protocol=proto, first_seen=when)
        ep.host = host
        ep.port = int(port) if port else None
        ep.name = name or ep.name
        ep.uri = uri or ep.uri
        ep.interface = interface or ep.interface
        ep.discovery = "passive traffic"
        ep.last_seen = when
        if evidence and evidence not in ep.evidence:
            ep.evidence.append(evidence)
        self._endpoints[key] = ep
        self.observations += 1
        self.last_observed_at = when
        self._trim()

    def _trim(self) -> None:
        if len(self._endpoints) <= self.max_endpoints:
            return
        for key, _ep in sorted(self._endpoints.items(), key=lambda kv: kv[1].last_seen)[: len(self._endpoints) - self.max_endpoints]:
            self._endpoints.pop(key, None)

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        endpoints = [ep.public(now, self.stale_after_s) for ep in self._endpoints.values()]
        endpoints.sort(key=lambda x: (not x["online"], x["protocol"], x.get("name") or x.get("host") or ""))
        protocols: dict[str, int] = {}
        for item in endpoints:
            protocols[item["protocol"]] = protocols.get(item["protocol"], 0) + 1
        return {
            "mode": "supervision_only",
            "enabled": self.enabled,
            "interface": self.interface,
            "preview_enabled": self.preview_enabled,
            "entities_created": 0,
            "active_probes": False,
            "stream_subscriptions": False,
            "control_available": False,
            "endpoint_count": len(endpoints),
            "online_count": sum(1 for item in endpoints if item["online"]),
            "protocols": protocols,
            "observations": self.observations,
            "last_observed_at": self.last_observed_at,
            "endpoints": endpoints,
            "notes": [
                "Supervision only: no Home Assistant sensor/entity is created by this module.",
                "NDI discovery evidence does not imply a playable URI; NDI SDK/plugin support is required to open NDI media.",
                "SRT has no generic discovery probe here; it is shown only when explicit passive evidence is observed.",
                "Low-quality preview is opt-in and opens a media subscription only while the preview is viewed.",
            ],
        }
