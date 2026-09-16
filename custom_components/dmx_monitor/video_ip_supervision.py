"""Unified, read-only IP-video source registry.

Combines whatever real evidence is available across three different kinds
of IP video, without ever fabricating a stream URL:

- **NDI** (``_ndi._tcp.local.``, a real, documented Bonjour/mDNS service
  type): identity only (name, host, addresses). NDI requires the
  proprietary NDI SDK to decode, so no generic HTTP/RTSP URI can play an
  NDI source in a browser -- ``preview_uri`` is always None for these,
  exactly as AUDIT_PHASE13_FINAL_ACCEPTANCE.md documents: "NDI is not
  synthesized into a fake stream URI".
- **ONVIF/RTSP cameras**: identity via mDNS where advertised; a
  ``preview_uri`` is only ever set from information the operator explicitly
  provided (e.g. a known RTSP/MJPEG URL), never guessed from a bare IP.
- **SMPTE ST 2110**: whatever st2110.py's SAP/SDP discovery already found,
  surfaced here too for a single consolidated inventory. Still no preview
  URI: raw ST 2110 video is uncompressed and not browser-playable without a
  transcoding step this integration does not perform.

This module never creates Home Assistant camera entities or sensors on its
own (per the README: "supervision séparée, sans création de sensors HA").

External transcoding bridge (optional, not implemented here)
--------------------------------------------------------------
Neither NDI nor raw ST 2110 is browser-playable as-is. If an operator runs
a *separate* transcoding bridge (e.g. an ffmpeg process using the NDI SDK,
or an ffmpeg RTP receiver for a specific ST 2110 flow) that republishes a
source as plain MJPEG/RTSP, that bridge -- once it exists -- can attach its
resulting URL to the matching, already-discovered source via
``set_preview_uri(key, uri)``. This module never starts, manages, or
assumes such a bridge is running; it only accepts the result if one already
is, the same way ``observe_rtsp``'s ``preview_uri`` is only ever an
explicitly supplied value.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

NDI_SERVICE_TYPE = "_ndi._tcp.local."
_STALE_AFTER_S = 60.0


@dataclass
class VideoSource:
    key: str
    kind: str  # "ndi" | "rtsp" | "st2110" | "other"
    name: str | None = None
    host: str | None = None
    addresses: tuple[str, ...] = field(default_factory=tuple)
    port: int | None = None
    preview_uri: str | None = None
    preview_source: str | None = None  # e.g. "operator", "external_bridge:ffmpeg-ndi" -- who supplied preview_uri
    evidence: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def snapshot(self, now: float, stale_after_s: float) -> dict[str, Any]:
        age = max(0.0, now - self.last_seen)
        return {
            "key": self.key,
            "kind": self.kind,
            "name": self.name,
            "host": self.host,
            "addresses": list(self.addresses),
            "port": self.port,
            "preview_uri": self.preview_uri,
            "preview_source": self.preview_source,
            "evidence": self.evidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "age_s": round(age, 1),
            "fresh": age < stale_after_s,
        }


class VideoIPSupervision:
    def __init__(self, stale_after_s: float = _STALE_AFTER_S) -> None:
        self.sources: dict[str, VideoSource] = {}
        self.stale_after_s = float(stale_after_s)
        self.discovery_errors: list[str] = []
        self.last_scan_monotonic: float | None = None

    # -- ingestion -----------------------------------------------------------
    def observe_ndi(self, name: str, host: str | None, addresses: list[str], *, evidence: str = "mDNS _ndi._tcp.local.") -> None:
        """NDI identity only. Never touches preview_uri -- see set_preview_uri()."""
        key = f"ndi:{name}"
        now = time.time()
        src = self.sources.get(key)
        if src is None:
            src = VideoSource(key=key, kind="ndi", first_seen=now)
            self.sources[key] = src
        src.name = name
        src.host = host or src.host
        src.addresses = tuple(addresses) or src.addresses
        src.evidence = evidence
        src.last_seen = now

    def observe_rtsp(self, name: str, host: str, *, addresses: list[str] | None = None, port: int | None = None,
                      preview_uri: str | None = None, evidence: str = "mDNS/manual") -> None:
        key = f"rtsp:{host}:{port or 0}"
        now = time.time()
        src = self.sources.get(key)
        if src is None:
            src = VideoSource(key=key, kind="rtsp", first_seen=now)
            self.sources[key] = src
        src.name = name or src.name
        src.host = host
        if addresses:
            src.addresses = tuple(addresses)
        if port is not None:
            src.port = port
        # A preview URI is only ever accepted from an explicit, known-good
        # value the caller supplied (e.g. an operator-entered RTSP/MJPEG URL
        # or one confirmed by a real camera-description response) -- never
        # synthesized here from a bare host/port guess.
        if preview_uri:
            src.preview_uri = preview_uri
            src.preview_source = "operator"
        src.evidence = evidence
        src.last_seen = now

    def observe_st2110(self, sdp_sessions: list[dict[str, Any]]) -> None:
        """Fold st2110.py's SDP-discovered flows into the same registry."""
        now = time.time()
        for row in sdp_sessions or ():
            dest = row.get("destination")
            port = row.get("port")
            if not dest or not port:
                continue
            key = f"st2110:{dest}:{port}"
            src = self.sources.get(key)
            if src is None:
                src = VideoSource(key=key, kind="st2110", first_seen=now)
                self.sources[key] = src
            src.name = row.get("name") or src.name
            src.host = dest
            src.port = int(port)
            src.evidence = f"SAP/SDP m=video ({row.get('rtpmap') or 'raw'})"
            src.last_seen = now

    # -- external transcoding bridge attachment ---------------------------------
    def set_preview_uri(self, key: str, uri: str, *, bridge_name: str = "external_bridge") -> bool:
        """Attach a real preview URL an external bridge is already serving.

        Only ever updates an already-known source (found by its ``key``, as
        seen in snapshot() rows); it never creates a source on its own and
        never guesses a URI. Returns False if ``key`` is unknown, so a
        caller can tell the difference between "attached" and "no such
        source (yet)".
        """
        src = self.sources.get(key)
        if src is None:
            return False
        src.preview_uri = uri
        src.preview_source = bridge_name
        return True

    def clear_preview_uri(self, key: str) -> None:
        """Detach a previously-attached bridge preview (e.g. the bridge stopped)."""
        src = self.sources.get(key)
        if src is not None:
            src.preview_uri = None
            src.preview_source = None

    async def async_poll_preview_bridge(self, base_url: str, *, timeout: float = 3.0) -> int:
        """Poll a running tools/video_preview_bridge/video_bridge.py instance.

        GETs ``<base_url>/status`` and, for every target it reports healthy,
        attaches ``<base_url>/preview/<key>`` as that source's preview_uri;
        for every target it no longer reports healthy, detaches any
        previously-attached preview. Returns the number of sources currently
        attached. Never raises on a network error (bridge not running yet is
        a completely normal state); errors are recorded in
        ``self.discovery_errors`` for the snapshot to surface instead.
        """
        import json as _json
        import urllib.error
        import urllib.request
        from urllib.parse import quote as _quote

        def _fetch() -> dict:
            with urllib.request.urlopen(f"{base_url.rstrip('/')}/status", timeout=timeout) as resp:
                return _json.loads(resp.read().decode("utf-8"))

        try:
            import asyncio as _asyncio
            data = await _asyncio.to_thread(_fetch)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self.discovery_errors = [f"preview bridge unreachable: {exc}"]
            return 0

        self.discovery_errors = [e for e in self.discovery_errors if not e.startswith("preview bridge unreachable")]
        attached = 0
        for target in data.get("targets", []):
            key = target.get("key")
            if not key or key not in self.sources:
                continue
            if target.get("healthy"):
                self.set_preview_uri(key, f"{base_url.rstrip('/')}/preview/{_quote(key, safe='')}", bridge_name="external_bridge:video_bridge.py")
                attached += 1
            else:
                self.clear_preview_uri(key)
        return attached

    # -- mDNS discovery --------------------------------------------------------
    async def async_scan_ndi(self, hass, timeout: float = 3.0) -> int:
        """Discover NDI sources via Home Assistant's shared Zeroconf instance."""
        try:
            from homeassistant.components import zeroconf as ha_zeroconf
        except ImportError:
            self.discovery_errors = ["homeassistant.components.zeroconf unavailable"]
            return 0

        try:
            zc = await ha_zeroconf.async_get_instance(hass)
            import asyncio as _asyncio

            found = await _asyncio.to_thread(self._scan_ndi_sync, zc, timeout)
        except Exception as exc:
            self.discovery_errors = [str(exc)]
            _LOGGER.debug("NDI mDNS scan failed", exc_info=True)
            return 0

        self.discovery_errors = []
        self.last_scan_monotonic = time.monotonic()
        for row in found:
            self.observe_ndi(row["name"], row.get("host"), row.get("addresses", []))
        return len(found)

    @staticmethod
    def _scan_ndi_sync(zc, timeout: float) -> list[dict[str, Any]]:
        try:
            from zeroconf import ServiceBrowser, ServiceListener
        except ImportError:
            return []

        found: dict[str, dict[str, Any]] = {}

        class Listener(ServiceListener):
            def add_service(self, zc, service_type, name):
                self._update(zc, service_type, name)

            def update_service(self, zc, service_type, name):
                self._update(zc, service_type, name)

            def remove_service(self, zc, service_type, name):
                found.pop(name, None)

            def _update(self, zc, service_type, name):
                try:
                    info = zc.get_service_info(service_type, name, timeout=1200)
                    if not info:
                        return
                    addresses = []
                    for addr in info.addresses_by_version(4):
                        try:
                            addresses.append(".".join(str(b) for b in addr))
                        except Exception:
                            continue
                    label = str(name).removesuffix(service_type).rstrip(".")
                    found[name] = {
                        "name": label or name,
                        "host": str(info.server or "").rstrip(".") or None,
                        "addresses": addresses,
                    }
                except Exception as exc:
                    _LOGGER.debug("NDI mDNS service parse failed for %s: %s", name, exc)

        browser = None
        try:
            listener = Listener()
            browser = ServiceBrowser(zc, NDI_SERVICE_TYPE, listener)
            import time as _time
            deadline = _time.monotonic() + max(0.5, min(timeout, 10.0))
            while _time.monotonic() < deadline:
                _time.sleep(0.05)
        finally:
            if browser is not None:
                try:
                    browser.cancel()
                except Exception:
                    pass
        return list(found.values())

    # -- reporting -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        rows = [src.snapshot(now, self.stale_after_s) for src in self.sources.values()]
        rows.sort(key=lambda r: (r["kind"], r["name"] or r["key"]))
        return {
            "video_ip_sources": rows,
            "video_ip_source_count": len(rows),
            "video_ip_fresh_count": sum(1 for r in rows if r["fresh"]),
            "video_ip_by_kind": {
                kind: sum(1 for r in rows if r["kind"] == kind)
                for kind in sorted({r["kind"] for r in rows})
            },
            "video_ip_discovery_errors": list(self.discovery_errors),
            "video_ip_note": (
                "NDI and raw ST 2110 sources never get a synthesized preview_uri "
                "(neither is browser-playable without proprietary/transcoding "
                "support this integration does not provide). RTSP preview_uri "
                "is only ever a value explicitly supplied by the operator or a "
                "confirmed camera response, never guessed from a bare address."
            ),
        }
