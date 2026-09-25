"""Resolume status monitor. Uses a real local HTTP server (Python's
http.server in a background thread) rather than mocking urlopen --
exercises the actual HTTP GET request/response cycle and JSON parsing
end to end.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from custom_components.dmx_monitor.resolume_monitor import ResolumeMonitor, _param_value



class _FakeResolumeServer:
    """Serves a real HTTP GET /api/v1/composition response shaped like
    Resolume's own documented/observed payload -- parameter values
    wrapped in {"value": ...} objects, layers/clips nesting."""

    def __init__(self, composition: dict, status_code: int = 200):
        self.composition = composition
        self.status_code = status_code
        self.received_paths: list[str] = []
        monitor_self = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                monitor_self.received_paths.append(self.path)
                body = json.dumps(monitor_self.composition).encode("utf-8")
                self.send_response(monitor_self.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A002 - silence test server logging
                pass

        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _composition_with_active_clip():
    return {
        "layers": [
            {
                "name": {"value": "Layer 1"},
                "clips": [
                    {"name": {"value": "Intro"}, "connected": {"value": "Disconnected", "valuetype": "ParamState"}},
                    {"name": {"value": "Loop A"}, "connected": {"value": "Connected", "valuetype": "ParamState"}},
                ],
            },
            {
                "name": {"value": "Layer 2 (text)"},
                "clips": [
                    {"name": {"value": "Lower Third"}, "connected": {"value": "Connected & previewing", "valuetype": "ParamState"}},
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_online_resolume_reports_active_clips_per_layer(socket_enabled):
    server = _FakeResolumeServer(_composition_with_active_clip())
    server.start()
    try:
        monitor = ResolumeMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()

        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["layer_count"] == 2
        assert row["active_layer_count"] == 2
        by_name = {l["name"]: l for l in row["layers"]}
        assert by_name["Layer 1"]["active"] is True
        assert by_name["Layer 1"]["playing_clip_name"] == "Loop A"
        assert by_name["Layer 2 (text)"]["playing_clip_name"] == "Lower Third"
        assert row["scope"] == "status_only_no_playback_control"

        # Confirms the real GET request actually hit the documented path.
        assert server.received_paths == ["/api/v1/composition"]
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_layer_with_no_connected_clip_is_not_active(socket_enabled):
    composition = {
        "layers": [
            {"name": {"value": "Idle layer"}, "clips": [
                {"name": {"value": "Clip A"}, "connected": {"value": "Disconnected"}},
                {"name": {"value": "Clip B"}, "connected": {"value": "Empty"}},
            ]},
        ],
    }
    server = _FakeResolumeServer(composition)
    server.start()
    try:
        monitor = ResolumeMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        layer = monitor.snapshot()[0]["layers"][0]
        assert layer["active"] is False
        assert layer["playing_clip_name"] is None
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_unreachable_host_reports_offline_not_a_crash(socket_enabled):
    monitor = ResolumeMonitor(["127.0.0.1"], port=1)  # port 1 is reserved, always connection-refused on loopback
    await monitor.async_update()
    row = monitor.snapshot()[0]
    assert row["online"] is False
    assert row["error"] is not None


@pytest.mark.asyncio
async def test_never_sends_anything_but_get_to_composition(socket_enabled):
    """The whole point of this module's narrow scope: it must never PUT
    or POST to trigger a clip/column -- guards against a future edit
    accidentally adding a control action."""
    server = _FakeResolumeServer(_composition_with_active_clip())
    server.start()
    try:
        monitor = ResolumeMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        assert all(p == "/api/v1/composition" for p in server.received_paths)
        assert not any("/connect" in p or "/open" in p for p in server.received_paths)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_empty_composition_reports_online_with_no_layers(socket_enabled):
    server = _FakeResolumeServer({"layers": []})
    server.start()
    try:
        monitor = ResolumeMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["layer_count"] == 0
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_no_hosts_is_a_noop(socket_enabled):
    monitor = ResolumeMonitor([])
    await monitor.async_update()
    assert monitor.snapshot() == []


def test_param_value_unwraps_wrapped_and_passes_through_raw():
    assert _param_value({"id": 1, "valuetype": "ParamState", "value": "Connected"}) == "Connected"
    assert _param_value("already-a-raw-string") == "already-a-raw-string"
    assert _param_value(None) is None
