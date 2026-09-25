"""Home Assistant HTTP views for the grandMA3 Web Remote HTTPS/WSS proxy.

SECURITY FIX (this revision): an external audit correctly flagged that the
first version of this file took ``station_ip`` straight from the URL and
used it to build an outbound request with no validation at all -- any
authenticated Home Assistant user could have pointed it at an arbitrary
internal host (SSRF), including cloud metadata endpoints or other internal
services reachable from the Home Assistant server. This revision:

1. Rejects anything that doesn't parse as a real IP address (no hostnames).
2. Only proxies to an IP that is *already present* in this config entry's
   own MA-Net3 station inventory (coordinator.ma_remote.stations) -- i.e.
   a console Show Network has itself passively observed on the network,
   never an arbitrary address the caller supplies.
3. Caps the upstream response body size instead of reading it unbounded.
4. Takes an explicit ``entry_id`` (matching video_ip_preview.py's existing
   pattern) instead of guessing an entry, closing the "first entry only"
   ambiguity the same audit raised for other views.

IMPORTANT -- testing status: this file uses aiohttp and Home Assistant's own
HomeAssistantView base class, neither of which could be installed in the
sandbox this project was developed in (no network access). It follows the
same pattern already established by video_ip_preview.py in this codebase.
This file's own aiohttp/HA-specific glue has not been executed anywhere.
Test it on-site against a real console before depending on it for a show.

Why this exists: ma_remote.py only ever computed a plain
http://<console-ip>:8080/ link (MAStation.web_remote_url) -- which fails
over HTTPS (Nabu Casa) because the console's own Web Remote page hardcodes
a plain ws:// WebSocket URL, which browsers refuse as mixed content when
the outer page is HTTPS. This view fixes that by acting as a same-origin
HTTPS/WSS front door that Home Assistant (and therefore Nabu Casa) already
serves, forwarding to the console in plain HTTP/WS behind the scenes.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging

from aiohttp import ClientSession, ClientTimeout, WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from . import DOMAIN
from .ma3_web_remote_proxy import rewrite_content

_LOGGER = logging.getLogger(__name__)

MA_WEB_REMOTE_PORT = 8080
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # generous for a Web Remote page/asset, not unbounded

# Two separate "what path does the WebSocket use" questions exist here, and
# only one is resolved:
#
# 1. Browser -> our proxy: RESOLVED. rewrite_content() hardcode-replaces the
#    console's own "ws://" + window.location.host construction with a full
#    URL pointing at MA3ProxyWebSocketView.url below.
#
# 2. Our proxy -> the real console: STILL UNVERIFIED. What path/query the
#    console's own WebSocket *server* actually listens on was never
#    confirmed against a packet capture. Verify on-site (browser DevTools ->
#    Network -> WS, load the *unproxied* page directly at
#    http://<console>:8080/) and update DEFAULT_CONSOLE_WS_PATH if needed.
DEFAULT_CONSOLE_WS_PATH = "/"


def _resolve_entry_and_coordinator(hass, entry_id: str):
    """Return (entry_id, coordinator) for a known entry, or (None, None)."""
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        values = entries.get(entry_id)
        coordinator = values.get("coordinator") if isinstance(values, dict) else None
        return (entry_id, coordinator) if coordinator else (None, None)
    # No entry_id given: only auto-resolve if there is exactly one entry,
    # matching this codebase's existing single-instance "hub" pattern
    # elsewhere; with more than one entry, require the caller to specify.
    candidates = [(eid, v.get("coordinator")) for eid, v in entries.items() if isinstance(v, dict) and v.get("coordinator")]
    if len(candidates) == 1:
        return candidates[0]
    return None, None


def _is_known_station(coordinator, station_ip: str) -> bool:
    """True only if station_ip is a real IP AND already observed on the
    network by this entry's own MA-Net3 listener -- never an arbitrary
    caller-supplied address."""
    try:
        ipaddress.ip_address(station_ip)
    except ValueError:
        return False
    ma_remote = getattr(coordinator, "ma_remote", None)
    if ma_remote is None:
        return False
    return station_ip in ma_remote.stations


class MA3ProxyHttpView(HomeAssistantView):
    """Proxies the Web Remote's HTML/JS/asset GET requests, rewriting
    ws:// to wss:// and injecting a <base> tag so relative assets resolve
    correctly under this view's own path prefix (see rewrite_content())."""

    url = "/api/dmx_monitor/ma_remote/{station_ip}/{path:.*}"
    name = "api:dmx_monitor:ma_remote_http"
    requires_auth = True

    async def get(self, request: web.Request, station_ip: str, path: str) -> web.Response:
        hass = request.app["hass"]
        entry_id, coordinator = _resolve_entry_and_coordinator(hass, str(request.query.get("entry_id") or ""))
        if coordinator is None:
            return web.Response(status=400, text="Missing or ambiguous entry_id (multiple Show Network entries exist)")
        if not _is_known_station(coordinator, station_ip):
            _LOGGER.warning("MA3 Web Remote proxy: rejected request for unknown/invalid station %r", station_ip)
            return web.Response(status=404, text="Unknown grandMA3 station: not in this entry's discovered MA-Net3 inventory")

        upstream_url = f"http://{station_ip}:{MA_WEB_REMOTE_PORT}/{path}"
        proxy_prefix = f"/api/dmx_monitor/ma_remote/{station_ip}"
        secure = request.headers.get("X-Forwarded-Proto", request.scheme).lower() == "https"

        try:
            timeout = ClientTimeout(total=5.0)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(upstream_url) as upstream:
                    content_length = upstream.headers.get("Content-Length")
                    if content_length and int(content_length) > _MAX_RESPONSE_BYTES:
                        return web.Response(status=502, text="Upstream response too large")
                    body = await upstream.content.read(_MAX_RESPONSE_BYTES + 1)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        return web.Response(status=502, text="Upstream response too large")
                    content_type = upstream.headers.get("Content-Type", "application/octet-stream")
        except Exception as exc:
            _LOGGER.warning("MA3 Web Remote proxy: could not reach %s: %s", upstream_url, exc)
            return web.Response(status=502, text=f"Cannot reach grandMA3 console at {station_ip}: {exc}")

        if "html" in content_type.lower() or "javascript" in content_type.lower():
            ws_proxy_path = f"/api/dmx_monitor/ma_remote_ws/{station_ip}?entry_id={entry_id}"
            body = rewrite_content(body, content_type, proxy_prefix, secure=secure, ws_proxy_path=ws_proxy_path)

        return web.Response(body=body, content_type=content_type.split(";")[0].strip())


class MA3ProxyWebSocketView(HomeAssistantView):
    """Bridges a browser's wss:// connection (through Home Assistant/Nabu
    Casa's own HTTPS) to the console's plain ws:// endpoint, using aiohttp's
    own WebSocketResponse/ClientSession.ws_connect (battle-tested, unlike
    the hand-rolled RFC 6455 engine in ma3_web_remote_proxy.py, which exists
    only to prove the relay logic correct in an environment without aiohttp
    available to test against)."""

    url = "/api/dmx_monitor/ma_remote_ws/{station_ip}"
    name = "api:dmx_monitor:ma_remote_ws"
    requires_auth = True

    async def get(self, request: web.Request, station_ip: str) -> web.WebSocketResponse:
        hass = request.app["hass"]
        _entry_id, coordinator = _resolve_entry_and_coordinator(hass, str(request.query.get("entry_id") or ""))
        if coordinator is None or not _is_known_station(coordinator, station_ip):
            _LOGGER.warning("MA3 Web Remote proxy: rejected WebSocket for unknown/invalid station %r", station_ip)
            raise web.HTTPNotFound(text="Unknown grandMA3 station")

        browser_ws = web.WebSocketResponse()
        await browser_ws.prepare(request)

        console_ws_url = f"ws://{station_ip}:{MA_WEB_REMOTE_PORT}{DEFAULT_CONSOLE_WS_PATH}"
        session = ClientSession()
        try:
            async with session.ws_connect(console_ws_url, timeout=5.0) as console_ws:

                async def browser_to_console():
                    async for msg in browser_ws:
                        if msg.type == WSMsgType.TEXT:
                            await console_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await console_ws.send_bytes(msg.data)
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
                            await console_ws.close()
                            return

                async def console_to_browser():
                    async for msg in console_ws:
                        if msg.type == WSMsgType.TEXT:
                            await browser_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await browser_ws.send_bytes(msg.data)
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
                            await browser_ws.close()
                            return

                await asyncio.gather(browser_to_console(), console_to_browser(), return_exceptions=True)
        except Exception as exc:
            _LOGGER.warning("MA3 Web Remote proxy: WebSocket bridge to %s failed: %s", station_ip, exc)
            if not browser_ws.closed:
                await browser_ws.close()
        finally:
            await session.close()

        return browser_ws


def async_register(hass) -> None:
    key = f"{DOMAIN}_ma3_proxy_registered"
    if hass.data.get(key):
        return
    hass.http.register_view(MA3ProxyHttpView)
    hass.http.register_view(MA3ProxyWebSocketView)
    hass.data[key] = True
