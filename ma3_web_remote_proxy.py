"""Core engine for the grandMA3 Web Remote HTTPS/WSS reverse proxy.

Diagnosis (confirmed by hand against a real console, see conversation):
Home Assistant can already reach the console's Web Remote directly
(``curl -I http://<console>:8080`` returns 200). The Web Remote's own
JavaScript hardcodes ``serverURI = "ws://" + window.location.host`` --
when the page is loaded over HTTPS (Nabu Casa), a browser refuses that
plain ``ws://`` request as mixed content, so the control link never opens
even though everything else works. A second, independent problem is that
the Web Remote's assets use paths assumed relative to the site root, which
breaks under any path-prefixed proxy (i.e. Ingress-style) unless the
document explicitly tells the browser what its effective base path is.

This module fixes both, without needing a separate TLS certificate: it is
meant to run *inside* Home Assistant's own aiohttp server (registered via
``hass.http.register_view``, see ma3_web_remote_view.py), so Nabu Casa (or
any other HTTPS front door already in front of Home Assistant) transparently
provides the TLS termination the console itself does not.

No third-party library is used here (neither ``aiohttp`` nor ``websockets``
could be installed in the environment this was developed/tested in), so
the WebSocket handshake and frame (de)coding are implemented directly from
RFC 6455. This is exactly the kind of thing this project already does
elsewhere (see snmp.py's hand-rolled ASN.1 BER) rather than depending on a
library that might not be present.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
import struct
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OPCODE_CONTINUATION = 0x0
_OPCODE_TEXT = 0x1
_OPCODE_BINARY = 0x2
_OPCODE_CLOSE = 0x8
_OPCODE_PING = 0x9
_OPCODE_PONG = 0xA


# ---------------------------------------------------------------------------
# Content rewriting (HTTP GET path)
# ---------------------------------------------------------------------------

def rewrite_content(content: bytes, content_type: str, proxy_prefix: str, secure: bool, *, ws_proxy_path: str | None = None) -> bytes:
    """Rewrite an HTML/JS response fetched from the console so it works when
    reloaded through ``proxy_prefix`` instead of the console's own root.

    - For HTML documents, a ``<base href="{proxy_prefix}/">`` tag is injected
      right after ``<head>`` (or prepended if no ``<head>`` tag is found).
      This is the general-purpose fix for the "assets built for the site
      root break under a path prefix" problem: every relative URL in the
      document (script/link/img src, relative fetch() calls, etc.) then
      resolves against the proxy prefix automatically, without needing to
      special-case each individual asset reference by hand.
    - If ``ws_proxy_path`` is given, the common
      ``"ws://" + window.location.host`` construction (and its
      template-literal equivalent, ``ws://${window.location.host}``) is
      hardcode-replaced with a full, correct WebSocket URL pointing at that
      exact proxy path -- this avoids depending on window.location.host
      alone landing the browser's WebSocket connection on the right path,
      which the relayed page cannot be relied on to do by itself (the
      original page hardcodes only a host, not a path, so where a
      literally-interpreted ``window.location.host`` construction would
      route to depends on things this proxy cannot control). The exact
      source line was not available when this was written -- this handles
      the documented pattern and common quoting/template-literal variants;
      if the real console's JS differs, the fallback below still upgrades
      ws:// to wss:// (which is necessary but not sufficient on its own).
    - Every remaining literal ``ws://`` becomes ``wss://`` when ``secure``
      is True, as a fallback for anything the targeted replacement above
      didn't match; left untouched otherwise, so a plain-HTTP on-site
      connection to Home Assistant still behaves exactly as before.
    """
    text = content.decode("utf-8", errors="replace")

    if ws_proxy_path:
        scheme = "wss" if secure else "ws"
        target = f'"{scheme}://" + window.location.host + "{ws_proxy_path}"'
        # "ws://" + window.location.host  (or location.host, single/double quotes)
        text = re.sub(
            r'''(["'])ws://\1\s*\+\s*(?:window\.)?location\.host''',
            target,
            text,
        )
        # `ws://${window.location.host}`  (template literal)
        text = re.sub(
            r'''`ws://\$\{(?:window\.)?location\.host\}`''',
            target,
            text,
        )

    if secure:
        text = text.replace("ws://", "wss://")

    ct = (content_type or "").lower()
    if "html" in ct:
        base_tag = f'<base href="{proxy_prefix.rstrip("/")}/">'
        if re.search(r"<head[^>]*>", text, re.IGNORECASE):
            text = re.sub(r"(<head[^>]*>)", r"\1" + base_tag, text, count=1, flags=re.IGNORECASE)
        else:
            text = base_tag + text

    return text.encode("utf-8")


# ---------------------------------------------------------------------------
# RFC 6455 WebSocket framing
# ---------------------------------------------------------------------------

@dataclass
class WSFrame:
    opcode: int
    payload: bytes
    fin: bool = True


def _mask(payload: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % 4] for i, b in enumerate(payload))


def encode_frame(opcode: int, payload: bytes, *, mask: bool) -> bytes:
    """Encode one RFC 6455 frame. ``mask`` must be True for client->server
    frames and False for server->client frames (the spec requires this)."""
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))  # FIN=1, no extensions
    length = len(payload)
    mask_bit = 0x80 if mask else 0x00
    if length < 126:
        header.append(mask_bit | length)
    elif length < 65536:
        header.append(mask_bit | 126)
        header += struct.pack("!H", length)
    else:
        header.append(mask_bit | 127)
        header += struct.pack("!Q", length)
    if mask:
        key = os.urandom(4)
        header += key
        payload = _mask(payload, key)
    return bytes(header) + payload


async def read_frame(reader: asyncio.StreamReader) -> WSFrame | None:
    """Read exactly one RFC 6455 frame, or None on clean EOF."""
    first_two = await reader.readexactly(2)
    if not first_two:
        return None
    b0, b1 = first_two
    fin = bool(b0 & 0x80)
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    if length == 126:
        length = struct.unpack("!H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", await reader.readexactly(8))[0]
    mask_key = await reader.readexactly(4) if masked else None
    payload = await reader.readexactly(length) if length else b""
    if masked and mask_key:
        payload = _mask(payload, mask_key)
    return WSFrame(opcode=opcode, payload=payload, fin=fin)


def compute_accept_key(client_key: str) -> str:
    digest = hashlib.sha1((client_key + _WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def make_client_key() -> str:
    return base64.b64encode(os.urandom(16)).decode("ascii")


async def read_http_headers(reader: asyncio.StreamReader) -> tuple[str, dict[str, str]]:
    """Read an HTTP/1.1 request or response line + headers (no body)."""
    request_line = (await reader.readline()).decode("iso-8859-1").strip()
    headers: dict[str, str] = {}
    while True:
        line = (await reader.readline()).decode("iso-8859-1")
        if not line or line in ("\r\n", "\n"):
            break
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return request_line, headers


async def client_websocket_handshake(host: str, port: int, path: str, *, timeout: float = 5.0) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Open a plain-``ws://`` connection to the console and perform the
    RFC 6455 client handshake. Returns the open (reader, writer) pair,
    positioned right after the handshake, ready for frame relay."""
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    key = make_client_key()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    writer.write(request.encode("ascii"))
    await writer.drain()
    status_line, headers = await asyncio.wait_for(read_http_headers(reader), timeout=timeout)
    if " 101 " not in f" {status_line} ":
        writer.close()
        raise ConnectionError(f"console rejected WebSocket upgrade: {status_line!r}")
    expected = compute_accept_key(key)
    if headers.get("sec-websocket-accept") != expected:
        writer.close()
        raise ConnectionError("console returned an invalid Sec-WebSocket-Accept")
    return reader, writer


async def server_accept_handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, *, timeout: float = 5.0) -> None:
    """Perform the server-side (browser-facing) RFC 6455 handshake.

    Reads the browser's HTTP Upgrade request and replies with 101 +
    Sec-WebSocket-Accept. Raises ConnectionError if the request does not
    look like a WebSocket upgrade. This is what the real Home Assistant
    view wraps aiohttp's own WebSocketResponse around; kept here too so the
    relay engine has a complete, dependency-free standalone path for
    testing (and, if ever needed, for running outside aiohttp entirely).
    """
    request_line, headers = await asyncio.wait_for(read_http_headers(reader), timeout=timeout)
    if not request_line.upper().startswith("GET"):
        raise ConnectionError(f"not a GET request: {request_line!r}")
    if headers.get("upgrade", "").lower() != "websocket":
        raise ConnectionError("missing Upgrade: websocket header")
    client_key = headers.get("sec-websocket-key")
    if not client_key:
        raise ConnectionError("missing Sec-WebSocket-Key header")
    accept = compute_accept_key(client_key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    writer.write(response.encode("ascii"))
    await writer.drain()


# ---------------------------------------------------------------------------
# Bidirectional relay
# ---------------------------------------------------------------------------

async def relay_websocket(
    browser_reader: asyncio.StreamReader,
    browser_writer: asyncio.StreamWriter,
    console_reader: asyncio.StreamReader,
    console_writer: asyncio.StreamWriter,
) -> None:
    """Pump frames both ways until either side closes.

    Frames from the browser arrive masked (per spec) and are forwarded to
    the console masked as well (the console expects a normal client, and
    from its point of view we *are* the client). Frames from the console
    arrive unmasked and are forwarded to the browser unmasked (we are the
    server from the browser's point of view). Only the mask bit/mechanics
    change at each hop; payload bytes are passed through unmodified -- this
    proxy never interprets the MA3 remote-control protocol itself.
    """

    async def browser_to_console() -> None:
        try:
            while True:
                frame = await read_frame(browser_reader)
                if frame is None or frame.opcode == _OPCODE_CLOSE:
                    console_writer.write(encode_frame(_OPCODE_CLOSE, b"", mask=True))
                    await console_writer.drain()
                    return
                console_writer.write(encode_frame(frame.opcode, frame.payload, mask=True))
                await console_writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            return

    async def console_to_browser() -> None:
        try:
            while True:
                frame = await read_frame(console_reader)
                if frame is None or frame.opcode == _OPCODE_CLOSE:
                    browser_writer.write(encode_frame(_OPCODE_CLOSE, b"", mask=False))
                    await browser_writer.drain()
                    return
                browser_writer.write(encode_frame(frame.opcode, frame.payload, mask=False))
                await browser_writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            return

    await asyncio.gather(browser_to_console(), console_to_browser(), return_exceptions=True)
