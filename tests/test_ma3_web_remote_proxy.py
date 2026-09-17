"""Tests for custom_components/dmx_monitor/ma3_web_remote_proxy.py.

Covers the content-rewriting logic (the actual fix for the grandMA3 Web
Remote's mixed-content problem under HTTPS) and the hand-rolled RFC 6455
WebSocket engine, which exists to prove the relay logic correct in an
environment without aiohttp available to test against -- the real
production code path (ma3_web_remote_view.py) uses aiohttp's own
WebSocketResponse/ClientSession instead.
"""
from __future__ import annotations

import asyncio

import pytest

from custom_components.dmx_monitor.ma3_web_remote_proxy import (
    compute_accept_key,
    encode_frame,
    read_frame,
    rewrite_content,
)


def test_rewrite_content_injects_base_href_for_html():
    html = b"<html><head><title>MA3</title></head><body></body></html>"
    out = rewrite_content(html, "text/html", "/api/dmx_monitor/ma_remote/regie1", secure=True)
    assert b'<base href="/api/dmx_monitor/ma_remote/regie1/">' in out


def test_rewrite_content_hardcodes_correct_websocket_target():
    js = b'var serverURI = "ws://" + window.location.host;'
    out = rewrite_content(js, "application/javascript", "/x", secure=True, ws_proxy_path="/api/dmx_monitor/ma_remote_ws/10.2.1.1")
    assert b"/api/dmx_monitor/ma_remote_ws/10.2.1.1" in out
    assert b"wss://" in out


def test_rewrite_content_handles_single_quotes_and_bare_location_host():
    variants = [
        b"var s = 'ws://' + window.location.host;",
        b'var s = "ws://" + location.host;',
    ]
    for js in variants:
        out = rewrite_content(js, "application/javascript", "/x", secure=True, ws_proxy_path="/proxy/ws")
        assert b"/proxy/ws" in out


def test_rewrite_content_falls_back_to_plain_ws_to_wss_swap_for_unrecognized_patterns():
    js = b'var x = "ws://something-else.example.com/custom";'
    out = rewrite_content(js, "application/javascript", "/x", secure=True, ws_proxy_path="/proxy/ws")
    assert b"wss://something-else.example.com/custom" in out


def test_rewrite_content_leaves_ws_untouched_when_not_secure():
    js = b'var s = "ws://" + window.location.host;'
    out = rewrite_content(js, "application/javascript", "/x", secure=False, ws_proxy_path="/proxy/ws")
    assert b"ws://" in out and b"wss://" not in out


def test_compute_accept_key_matches_rfc6455_official_example():
    # The exact test vector from RFC 6455 section 1.3.
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    expected = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
    assert compute_accept_key(key) == expected


@pytest.mark.asyncio
async def test_frame_encode_decode_roundtrip():
    payload = b"Hello, grandMA3!"
    encoded = encode_frame(0x1, payload, mask=True)  # text frame, client->server style

    reader = asyncio.StreamReader()
    reader.feed_data(encoded)
    reader.feed_eof()

    frame = await read_frame(reader)
    assert frame is not None
    assert frame.payload == payload
