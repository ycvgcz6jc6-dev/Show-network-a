"""Generic device web-page proxy.

Lets an operator open a discovered device's own web management page from
inside Home Assistant, including remotely (e.g. via Nabu Casa), by having
Home Assistant itself -- which sits on the local network -- fetch the page
and relay it back over HA's own already-remote-accessible connection.

This deliberately solves two real problems at once:
  - Mixed content: the browser only ever loads from HA's own HTTPS origin;
    it never has to load an http:// resource directly, so browsers never
    block it as mixed content.
  - Local-network reachability: a device's own IP (e.g. 10.4.1.3) is not
    reachable from a phone on 4G outside the venue's network at all. HA
    does the fetch locally and relays the bytes; the remote browser only
    ever talks to HA.

Gated behind Show Network's security unlock, matching every other
active-adjacent surface in this project: exposing a device's own web UI
(even read-only pages can sometimes embed control forms) through a public
tunnel is exactly the kind of surface that should require the same
deliberate unlock as active outputs, not be open by default.

SSRF prevention follows the exact same pattern as ma3_web_remote_view.py:
the target IP must already be present in this entry's own discovered
device inventory. An arbitrary caller-supplied IP/host is never fetched.
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

import aiohttp
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .web_proxy_security import is_proxy_eligible_device_ip, validate_port, validated_redirect

_LOGGER = logging.getLogger(__name__)
MAX_BODY = 4 * 1024 * 1024  # 4 MiB is generous for a device's own management page
FETCH_TIMEOUT_S = 8


def _resolve_entry_and_coordinator(hass, entry_id: str):
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        values = entries.get(entry_id)
        coordinator = values.get("coordinator") if isinstance(values, dict) else None
        return (entry_id, coordinator) if coordinator else (None, None)
    candidates = [(eid, v.get("coordinator")) for eid, v in entries.items() if isinstance(v, dict) and v.get("coordinator")]
    if len(candidates) == 1:
        return candidates[0]
    return None, None


def _is_known_device_ip(coordinator, ip: str) -> bool:
    """Compatibility wrapper around the audited pure SSRF policy."""
    return is_proxy_eligible_device_ip(coordinator, ip)


class DeviceWebProxyView(HomeAssistantView):
    """GET /api/dmx_monitor/device_proxy/{ip}/{path:.*}?entry_id=...&port=...&scheme=..."""

    url = "/api/dmx_monitor/device_proxy/{ip}/{path:.*}"
    name = "api:dmx_monitor:device_proxy"
    requires_auth = True

    async def get(self, request: web.Request, ip: str, path: str) -> web.Response:
        hass = request.app["hass"]
        entry_id, coordinator = _resolve_entry_and_coordinator(hass, str(request.query.get("entry_id") or ""))
        if coordinator is None:
            return web.Response(status=400, text="Missing or ambiguous entry_id (multiple Show Network entries exist)")
        if not _is_known_device_ip(coordinator, ip):
            _LOGGER.warning("Device web proxy: rejected request for unknown/invalid device %r", ip)
            return web.Response(status=404, text="Unknown device: not in this entry's discovered inventory")
        try:
            coordinator.security.require_unlocked()
        except PermissionError as exc:
            return web.Response(status=403, text=f"Show Network is locked: {exc}")

        scheme = "https" if str(request.query.get("scheme") or "").lower() == "https" else "http"
        try:
            port = validate_port(request.query.get("port"), 443 if scheme == "https" else 80)
        except (TypeError, ValueError):
            return web.Response(status=400, text="Invalid port")
        target = f"{scheme}://{ip}:{port}/{path}"
        if request.query_string and "entry_id" not in path:
            # Forward any additional query params the device's own page needs,
            # stripping our own routing params.
            extra = {k: v for k, v in request.query.items() if k not in ("entry_id", "port", "scheme")}
            if extra:
                target += "?" + urlencode(extra)

        session = async_get_clientsession(hass)
        try:
            current = target
            for redirect_count in range(6):
                async with session.get(current, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S), ssl=False, allow_redirects=False) as resp:
                    if resp.status in (301, 302, 303, 307, 308):
                        if redirect_count >= 5:
                            return web.Response(status=502, text="Too many device redirects")
                        nxt = validated_redirect(current, resp.headers.get("Location", ""), ip)
                        if nxt is None:
                            _LOGGER.warning("Device web proxy: rejected unsafe redirect from %s to %r", current, resp.headers.get("Location"))
                            return web.Response(status=502, text="Device redirect rejected by proxy security policy")
                        current = nxt
                        continue
                    body = bytearray()
                    async for chunk in resp.content.iter_chunked(16384):
                        body.extend(chunk)
                        if len(body) > MAX_BODY:
                            return web.Response(status=502, text="Device page exceeds proxy size limit")
                    content_type = resp.headers.get("Content-Type", "text/html")
                    return web.Response(body=bytes(body), status=resp.status, content_type=content_type.split(";")[0].strip())
            return web.Response(status=502, text="Too many device redirects")
        except Exception as exc:
            _LOGGER.warning("Device web proxy: fetch to %s failed: %s", target, exc)
            return web.Response(status=502, text=f"Could not reach device: {exc}")


def async_register(hass) -> None:
    hass.http.register_view(DeviceWebProxyView)
