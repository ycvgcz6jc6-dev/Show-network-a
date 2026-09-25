"""Phase C23 (rapport maître, S113): 'Web Remote: UNKNOWN / AVAILABLE /
UNAVAILABLE.' Uses a real RFC 6455 WebSocket server (a real listening
server that performs the genuine handshake math and sends a real framed
reply) and a real closed port -- not mocked sockets -- exercising the
actual MARemoteInventory.async_probe_web_remote() integration end to
end. Low-level frame/handshake parsing is covered separately and more
exhaustively in test_ma_remote_websocket_probe_c23.py; this file covers
the higher-level station-tracking behaviour built on top of it.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import socket

import pytest

from custom_components.dmx_monitor.ma_remote import MARemoteInventory, MA_WEB_REMOTE_PORT, _WEBSOCKET_GUID

pytestmark = pytest.mark.asyncio


def _encode_ws_text_frame(payload: bytes) -> bytes:
    header = bytes([0x81])
    length = len(payload)
    if length < 126:
        header += bytes([length])
    else:
        header += bytes([126]) + length.to_bytes(2, "big")
    return header + payload


async def _start_real_ws_server(reply_status: str | None = "server ready"):
    async def _handle(reader, writer):
        try:
            header_bytes = await reader.readuntil(b"\r\n\r\n")
            header_text = header_bytes.decode("ascii")
            key = next(
                line.split(":", 1)[1].strip()
                for line in header_text.split("\r\n")
                if line.lower().startswith("sec-websocket-key:")
            )
            accept = base64.b64encode(hashlib.sha1((key + _WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                b"Sec-WebSocket-Accept: " + accept.encode("ascii") + b"\r\n\r\n"
            )
            await writer.drain()
            if reply_status is not None:
                writer.write(_encode_ws_text_frame(json.dumps({"status": reply_status}).encode("utf-8")))
                await writer.drain()
        except (OSError, asyncio.IncompleteReadError, StopIteration):
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(_handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    return server, port


def _find_closed_port() -> int:
    """A port nothing is listening on, on loopback -- a real connection
    refused, not a mock."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def test_station_starts_unknown_before_any_probe():
    inv = MARemoteInventory()
    inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
    assert inv.stations["127.0.0.1"].web_remote == "unknown"
    assert inv.snapshot()["diagnostics"]["web_remote_probe"] is False


async def test_probe_marks_real_web_remote_available(socket_enabled, monkeypatch):
    server, port = await _start_real_ws_server(reply_status="server ready")
    monkeypatch.setattr("custom_components.dmx_monitor.ma_remote.MA_WEB_REMOTE_PORT", port)
    try:
        inv = MARemoteInventory()
        inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
        await inv.async_probe_web_remote()
        assert inv.stations["127.0.0.1"].web_remote == "available"
        assert inv.snapshot()["diagnostics"]["web_remote_probe"] == "websocket_handshake"
    finally:
        server.close()
        await server.wait_closed()


async def test_probe_marks_closed_port_unavailable(socket_enabled, monkeypatch):
    closed_port = _find_closed_port()
    monkeypatch.setattr("custom_components.dmx_monitor.ma_remote.MA_WEB_REMOTE_PORT", closed_port)
    inv = MARemoteInventory()
    inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
    await inv.async_probe_web_remote()
    assert inv.stations["127.0.0.1"].web_remote == "unavailable"


async def test_probe_marks_non_grandma_service_unavailable(socket_enabled, monkeypatch):
    """A plain TCP listener that isn't a genuine grandMA3 Web Remote
    (doesn't even attempt a WebSocket handshake) must read as
    unavailable now -- the whole point of the upgrade from a bare TCP
    connect, which would have reported this as 'available'."""
    async def _handle(reader, writer):
        writer.close()

    server = await asyncio.start_server(_handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    monkeypatch.setattr("custom_components.dmx_monitor.ma_remote.MA_WEB_REMOTE_PORT", port)
    try:
        inv = MARemoteInventory()
        inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
        await inv.async_probe_web_remote()
        assert inv.stations["127.0.0.1"].web_remote == "unavailable"
    finally:
        server.close()
        await server.wait_closed()


async def test_repeated_observe_calls_do_not_reset_probe_result(socket_enabled, monkeypatch):
    """observe() fires on every received MA-Net3 packet -- i.e.
    constantly for an active station. It must never silently reset an
    already-probed web_remote status back to 'unknown'."""
    server, port = await _start_real_ws_server(reply_status="server ready")
    monkeypatch.setattr("custom_components.dmx_monitor.ma_remote.MA_WEB_REMOTE_PORT", port)
    try:
        inv = MARemoteInventory()
        inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
        await inv.async_probe_web_remote()
        assert inv.stations["127.0.0.1"].web_remote == "available"

        # Simulate more MA-Net3 traffic arriving after the probe ran.
        inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
        inv.observe("127.0.0.1", "239.0.0.1", session_index=1)

        assert inv.stations["127.0.0.1"].web_remote == "available", "must not have been reset to 'unknown'"
    finally:
        server.close()
        await server.wait_closed()


async def test_probe_with_no_stations_is_a_noop(socket_enabled):
    inv = MARemoteInventory()
    await inv.async_probe_web_remote()  # must not raise
    assert inv.stations == {}


async def test_snapshot_includes_web_remote_field_per_station():
    inv = MARemoteInventory()
    inv.observe("127.0.0.1", "239.0.0.1", session_index=1)
    row = inv.snapshot()["stations"][0]
    assert row["web_remote"] == "unknown"
    assert row["web_remote_url"] == f"http://127.0.0.1:{MA_WEB_REMOTE_PORT}"
