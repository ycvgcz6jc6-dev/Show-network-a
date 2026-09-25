"""Tests for rdm_bridge.py's RDMBridgeMonitor. No test previously
existed for this module. Uses a real local HTTP server (Python's
http.server in a background thread) rather than mocking urlopen.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from custom_components.dmx_monitor.rdm_bridge import RDMBridgeMonitor



class _FakeRDMBridgeServer:
    def __init__(self, devices=None, status_code=200):
        self.devices = devices if devices is not None else []
        self.status_code = status_code
        self.received_paths: list[str] = []
        self.received_methods: list[str] = []
        self.received_bodies: list[bytes] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.received_paths.append(self.path)
                outer.received_methods.append("GET")
                body = json.dumps({"devices": outer.devices}).encode("utf-8")
                self.send_response(outer.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                outer.received_paths.append(self.path)
                outer.received_methods.append("POST")
                outer.received_bodies.append(self.rfile.read(length))
                body = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
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


def test_unconfigured_bridge_reports_not_configured():
    monitor = RDMBridgeMonitor("", transport="RDM/OLA")
    assert monitor.configured is False


def test_configured_requires_http_scheme():
    assert RDMBridgeMonitor("http://10.4.1.5:9090", transport="RDM/OLA").configured is True
    assert RDMBridgeMonitor("https://10.4.1.5:9090", transport="RDM/OLA").configured is True
    assert RDMBridgeMonitor("10.4.1.5:9090", transport="RDM/OLA").configured is False


@pytest.mark.asyncio
async def test_async_update_fetches_devices_from_real_server(socket_enabled):
    server = _FakeRDMBridgeServer(devices=[{"uid": "1234:abcdef01", "device_label": "Dimmer 1"}])
    server.start()
    try:
        monitor = RDMBridgeMonitor(f"http://127.0.0.1:{server.port}", transport="RDM/OLA")
        await monitor.async_update()
        assert monitor.error is None
        assert monitor.devices == [{"uid": "1234:abcdef01", "device_label": "Dimmer 1"}]
        assert monitor.last_success is not None
        assert server.received_paths == ["/v1/devices"]
        assert server.received_methods == ["GET"]
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_update_drops_rows_without_uid(socket_enabled):
    """A row with no uid can't be tracked by RDMInventory (which keys on
    uid) -- must be filtered out here rather than passed through."""
    server = _FakeRDMBridgeServer(devices=[
        {"uid": "1234:abcdef01", "device_label": "Has UID"},
        {"device_label": "Missing UID"},
    ])
    server.start()
    try:
        monitor = RDMBridgeMonitor(f"http://127.0.0.1:{server.port}", transport="RDM/OLA")
        await monitor.async_update()
        assert len(monitor.devices) == 1
        assert monitor.devices[0]["uid"] == "1234:abcdef01"
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_update_unreachable_server_sets_error_not_a_crash(socket_enabled):
    monitor = RDMBridgeMonitor("http://127.0.0.1:1", transport="RDM/OLA", timeout=1.0)  # port 1 reserved, refused
    await monitor.async_update()
    assert monitor.error is not None
    assert monitor.devices == []


@pytest.mark.asyncio
async def test_unconfigured_bridge_clears_devices_without_network_call():
    monitor = RDMBridgeMonitor("", transport="RDMnet")
    monitor.devices = [{"uid": "stale:00000001"}]
    await monitor.async_update()
    assert monitor.devices == []
    assert monitor.error is None


@pytest.mark.asyncio
async def test_async_set_sends_real_post_with_expected_payload(socket_enabled):
    server = _FakeRDMBridgeServer()
    server.start()
    try:
        monitor = RDMBridgeMonitor(f"http://127.0.0.1:{server.port}", transport="RDM/OLA")
        result = await monitor.async_set(uid="1234:abcdef01", universe=3, pid="IDENTIFY_DEVICE", value=1)
        assert result == {"ok": True}
        assert server.received_methods == ["POST"]
        assert server.received_paths == ["/v1/set"]
        sent = json.loads(server.received_bodies[0])
        assert sent == {"uid": "1234:abcdef01", "pid": "IDENTIFY_DEVICE", "value": 1, "universe": 3}
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_set_on_unconfigured_bridge_raises():
    monitor = RDMBridgeMonitor("", transport="RDM/OLA")
    with pytest.raises(RuntimeError):
        await monitor.async_set(uid="1234:abcdef01", pid="IDENTIFY_DEVICE", value=1)


def test_snapshot_key_prefix_differs_by_transport():
    rdm = RDMBridgeMonitor("http://x", transport="RDM/OLA")
    rdmnet = RDMBridgeMonitor("http://x", transport="RDMnet")
    assert "rdm_bridge_configured" in rdm.snapshot()
    assert "rdmnet_bridge_configured" in rdmnet.snapshot()


@pytest.mark.asyncio
async def test_oversized_response_is_rejected(socket_enabled):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            huge = json.dumps({"devices": [{"uid": "1:1", "pad": "x" * (2 * 1024 * 1024 + 100)}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(huge)))
            self.end_headers()
            self.wfile.write(huge)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monitor = RDMBridgeMonitor(f"http://127.0.0.1:{port}", transport="RDM/OLA")
        await monitor.async_update()
        assert monitor.error is not None
        assert "too large" in monitor.error
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
