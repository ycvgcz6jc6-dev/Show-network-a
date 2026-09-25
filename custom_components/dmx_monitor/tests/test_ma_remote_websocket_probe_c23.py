"""Phase C23 web_remote probe upgrade: real RFC 6455 WebSocket handshake
instead of a bare TCP connect. Tested against a real, hand-rolled
WebSocket server (not a mocked socket) that performs the actual
handshake math (Sec-WebSocket-Accept = base64(sha1(key + GUID))) and
sends a real, correctly-framed WebSocket text frame -- exercising the
client's real wire parsing, not just its surrounding logic.

Grounded in a real grandMA3 Web Remote page's own client-side JS
(interface.js): connects to ws://host:port/?ma=1 and expects
{"status": "server ready"} as the server's first message.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import socket

import pytest

from custom_components.dmx_monitor.ma_remote import _probe_web_remote_handshake, _WEBSOCKET_GUID

pytestmark = pytest.mark.asyncio


def _encode_ws_text_frame(payload: bytes) -> bytes:
    """A minimal, correct RFC 6455 server->client (unmasked) text frame."""
    header = bytes([0x81])  # FIN=1, opcode=1 (text)
    length = len(payload)
    if length < 126:
        header += bytes([length])
    elif length < 65536:
        header += bytes([126]) + length.to_bytes(2, "big")
    else:
        header += bytes([127]) + length.to_bytes(8, "big")
    return header + payload


class _RealWebSocketServer:
    """A genuine RFC 6455 WebSocket server: reads the real HTTP Upgrade
    request, computes the real Sec-WebSocket-Accept, and sends back a
    real WebSocket frame -- everything a real grandMA3 Web Remote's own
    server side would do for this handshake."""

    def __init__(self, reply_status: str | None = "server ready", *, send_bad_accept=False,
                 send_non_101=False, send_binary_frame=False, close_before_frame=False):
        self.reply_status = reply_status
        self.send_bad_accept = send_bad_accept
        self.send_non_101 = send_non_101
        self.send_binary_frame = send_binary_frame
        self.close_before_frame = close_before_frame
        self.server = None
        self.port = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def _handle(self, reader, writer):
        try:
            header_bytes = await reader.readuntil(b"\r\n\r\n")
            header_text = header_bytes.decode("ascii")
            key = None
            for line in header_text.split("\r\n"):
                if line.lower().startswith("sec-websocket-key:"):
                    key = line.split(":", 1)[1].strip()
            if self.send_non_101:
                writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
                await writer.drain()
                return
            if self.send_bad_accept:
                accept = base64.b64encode(b"wrong-value-not-matching").decode("ascii")
            else:
                accept = base64.b64encode(hashlib.sha1((key + _WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: websocket\r\n"
                b"Connection: Upgrade\r\n"
                b"Sec-WebSocket-Accept: " + accept.encode("ascii") + b"\r\n\r\n"
            )
            await writer.drain()
            if self.close_before_frame:
                return
            if self.reply_status is not None:
                payload = json.dumps({"status": self.reply_status}).encode("utf-8")
                if self.send_binary_frame:
                    frame = bytes([0x82]) + bytes([len(payload)]) + payload  # opcode=2 (binary)
                else:
                    frame = _encode_ws_text_frame(payload)
                writer.write(frame)
                await writer.drain()
        except (OSError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    def stop(self):
        if self.server:
            self.server.close()


async def test_real_handshake_with_server_ready_reports_available(socket_enabled):
    server = _RealWebSocketServer(reply_status="server ready")
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is True
    finally:
        server.stop()


async def test_real_handshake_with_different_status_reports_unavailable(socket_enabled):
    """A server that completes the WS handshake but never sends the
    expected 'server ready' status must not be treated as available --
    this is the whole point of going beyond a bare TCP connect."""
    server = _RealWebSocketServer(reply_status="something else entirely")
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is False
    finally:
        server.stop()


async def test_non_websocket_http_server_reports_unavailable(socket_enabled):
    server = _RealWebSocketServer(send_non_101=True)
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is False
    finally:
        server.stop()


async def test_forged_accept_header_is_rejected(socket_enabled):
    """A server claiming 101 Switching Protocols but with a wrong
    Sec-WebSocket-Accept (i.e. not a genuine RFC 6455 peer) must be
    rejected -- this is exactly what distinguishes this probe from a
    bare TCP connect that a non-WebSocket service could also answer."""
    server = _RealWebSocketServer(send_bad_accept=True)
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is False
    finally:
        server.stop()


async def test_binary_frame_instead_of_text_is_rejected(socket_enabled):
    """The real protocol sends JSON as a text frame (opcode 1). A binary
    frame (opcode 2, used by this same protocol for image data per
    interface.js's own `myDecoder.handleImageData`) must not be
    misread as the status reply."""
    server = _RealWebSocketServer(reply_status="server ready", send_binary_frame=True)
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is False
    finally:
        server.stop()


async def test_connection_closed_after_handshake_before_frame_reports_unavailable(socket_enabled):
    server = _RealWebSocketServer(close_before_frame=True)
    await server.start()
    try:
        result = await _probe_web_remote_handshake("127.0.0.1", server.port, timeout=2.0)
        assert result is False
    finally:
        server.stop()


async def test_no_listener_at_all_reports_unavailable_not_a_crash(socket_enabled):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    closed_port = s.getsockname()[1]
    s.close()
    result = await _probe_web_remote_handshake("127.0.0.1", closed_port, timeout=1.0)
    assert result is False


async def test_never_sends_a_remotestate_or_video_request():
    """The whole point of stopping at the handshake reply: never send a
    requestType message (remoteState/requestVideo/resizeVideo) that the
    real client only sends *after* observing 'server ready'. Checked at
    the level of what's actually written to the wire (writer.write
    calls), not the whole source text, since the function's own
    docstring legitimately names these messages while explaining why
    they're avoided."""
    import ast
    import inspect
    from custom_components.dmx_monitor import ma_remote

    source = inspect.getsource(ma_remote._probe_web_remote_handshake)
    tree = ast.parse(source)
    writes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "write":
            writes.append(ast.get_source_segment(source, node) or "")
    assert writes, "expected at least the HTTP upgrade request to be written"
    for forbidden in ("remoteState", "requestVideo", "resizeVideo"):
        assert not any(forbidden in w for w in writes), f"{forbidden} must never be written to the wire"
