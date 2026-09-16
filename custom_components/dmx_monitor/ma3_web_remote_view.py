"""Home Assistant HTTP views for the grandMA3 Web Remote HTTPS/WSS proxy.

IMPORTANT -- testing status: this file uses aiohttp and Home Assistant's own
HomeAssistantView base class, neither of which could be installed in the
sandbox this project was developed in (no network access). It follows the
same pattern already established by video_ip_preview.py in this codebase
(class-level registration via hass.http.register_view(ViewClass), hass
retrieved per-request via request.app["hass"]) and reuses rewrite_content()
from ma3_web_remote_proxy.py, which *was* fully tested standalone. This
file's own aiohttp/HA-specific glue has not been executed anywhere. Test it
on-site against a real console before depending on it for a show.

Why this exists: ma_remote.py only ever computed a plain
http://<console-ip>:8080/ link (MAStation.web_remote_url) -- which fails
over HTTPS (Nabu Casa) because the console's own Web Remote page hardcodes
a plain ws:// WebSocket URL, which browsers refuse as mixed content when
the outer page is HTTPS. This view fixes that by acting as a same-origin
HTTPS/WSS front door that Home Assistant (and therefore Nabu Casa) already
serves, forwarding to the console in plain HTTP/WS behind the scenes --
implemented as a native Home Assistant view rather than add-on-oriented
Ingress (which does not apply to a custom_component), avoiding the
path-rewriting pitfalls Ingress caused during the original diagnosis.
"""
from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientSession, ClientTimeout, WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from . import DOMAIN
from .ma3_web_remote_proxy import rewrite_content

_LOGGER = logging.getLogger(__name__)

MA_WEB_REMOTE_PORT = 8080

# Two separate "what path does the WebSocket use" questions exist here, and
# only one is resolved:
#
# 1. Browser -> our proxy: RESOLVED. rewrite_content() hardcode-replaces the
#    console's own "ws://" + window.location.host construction with a full
#    URL pointing at MA3ProxyWebSocketView.url below, so the browser's
#    WebSocket request always lands exactly where we tell it to.
#
# 2. Our proxy -> the real console: STILL UNVERIFIED. What path/query the
#    console's own WebSocket *server* actually listens on (root? something
#    involving the "/?ma=1" reference found during the original diagnosis?)
#    was never confirmed against a packet capture or the exact captured
#    JavaScript line. Verify on-site (browser DevTools -> Network -> WS,
#    load the *unproxied* page directly at http://<console>:8080/) and
#    update DEFAULT_CONSOLE_WS_PATH below if it turns out to be something
#    else.
DEFAULT_CONSOLE_WS_PATH = "/"


def _console_base_url(station_ip: str) -> str:
    return f"http://{station_ip}:{MA_WEB_REMOTE_PORT}"


class MA3ProxyHttpView(HomeAssistantView):
    """Proxies the Web Remote's HTML/JS/asset GET requests, rewriting
    ws:// to wss:// and injecting a <base> tag so relative assets resolve
    correctly under this view's own path prefix (see rewrite_content())."""

    url = "/api/dmx_monitor/ma_remote/{station_ip}/{path:.*}"
    name = "api:dmx_monitor:ma_remote_http"
    requires_auth = True

    async def get(self, request: web.Request, station_ip: str, path: str) -> web.Response:
        upstream_url = f"{_console_base_url(station_ip)}/{path}"
        proxy_prefix = f"/api/dmx_monitor/ma_remote/{station_ip}"
        secure = request.headers.get("X-Forwarded-Proto", request.scheme).lower() == "https"

        try:
            timeout = ClientTimeout(total=5.0)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(upstream_url) as upstream:
                    body = await upstream.read()
                    content_type = upstream.headers.get("Content-Type", "application/octet-stream")
        except Exception as exc:
            _LOGGER.warning("MA3 Web Remote proxy: could not reach %s: %s", upstream_url, exc)
            return web.Response(status=502, text=f"Cannot reach grandMA3 console at {station_ip}: {exc}")

        if "html" in content_type.lower() or "javascript" in content_type.lower():
            ws_proxy_path = f"/api/dmx_monitor/ma_remote_ws/{station_ip}"
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
