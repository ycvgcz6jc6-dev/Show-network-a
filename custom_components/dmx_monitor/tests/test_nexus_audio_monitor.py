"""Nexus Audio gateway status monitor. Uses a real local HTTP server
(Python's http.server, matching the add-on's own implementation style)
rather than mocking urlopen. Response shapes below are taken directly
from the add-on's real source code (Worker.status() in app/main.py),
not guessed.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from custom_components.dmx_monitor.nexus_audio_monitor import NexusAudioMonitor

pytestmark = pytest.mark.asyncio


class _FakeNexusAudioServer:
    def __init__(self, health: dict, sources: dict | None = None):
        self.health = health
        self.sources = sources if sources is not None else {"sources": [], "validation_errors": []}
        self.received_paths: list[str] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.received_paths.append(self.path)
                if self.path == "/health":
                    payload = outer.health
                elif self.path == "/api/sources":
                    payload = outer.sources
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                outer.received_paths.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
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


def _real_source_row(**overrides) -> dict:
    """Shape taken directly from Worker.status() in the real add-on's
    app/main.py, not guessed."""
    row = {
        "id": "shure_rx", "name": "Shure Dante 1-2", "type": "dante_rx",
        "dante_mode": "native_dante", "interface": "enp10s0", "interface_ip": "10.4.1.20",
        "channels": 2, "sample_rate": 48000, "state": "running", "process_alive": True,
        "pid": 4242, "started_at": 1000.0, "uptime_s": 3600.0, "restarts": 0,
        "last_restart_at": None, "fifo": "/data/runtime/shure_rx/audio.pcm", "error": None,
        "audio": {"present": True, "last_audio_age_s": 0.1, "bytes_read": 999999, "peak_dbfs": -12.3},
        "process_metrics": {}, "dante": {}, "aes67": None, "sendspin": {}, "log_tail": [],
    }
    row.update(overrides)
    return row


async def test_online_gateway_reports_version_and_sources(socket_enabled):
    server = _FakeNexusAudioServer(
        health={"status": "ok", "version": "1.0.0-rc5", "validation_errors": []},
        sources={"sources": [_real_source_row()], "validation_errors": []},
    )
    server.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()

        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["version"] == "1.0.0-rc5"
        assert row["source_count"] == 1
        src = row["sources"][0]
        assert src["id"] == "shure_rx"
        assert src["state"] == "running"
        assert src["process_alive"] is True
        assert src["audio_present"] is True
        assert src["peak_dbfs"] == -12.3
        assert row["scope"] == "status_only_no_source_control"

        assert set(server.received_paths) == {"/health", "/api/sources"}
    finally:
        server.stop()


async def test_config_validation_errors_are_surfaced(socket_enabled):
    server = _FakeNexusAudioServer(
        health={"status": "config_error", "version": "1.0.0-rc5",
                "validation_errors": ["source 'x': alt_port collides with 'y'"]},
    )
    server.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["validation_errors"] == ["source 'x': alt_port collides with 'y'"]
    finally:
        server.stop()


async def test_source_with_no_audio_reports_not_present(socket_enabled):
    server = _FakeNexusAudioServer(
        health={"status": "ok", "version": "1.0.0-rc5"},
        sources={"sources": [_real_source_row(
            state="stopped", process_alive=False, pid=None,
            audio={"present": False, "last_audio_age_s": None, "bytes_read": 0, "peak_dbfs": None},
        )]},
    )
    server.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        src = monitor.snapshot()[0]["sources"][0]
        assert src["audio_present"] is False
        assert src["peak_dbfs"] is None
        assert src["process_alive"] is False
    finally:
        server.stop()


async def test_source_without_id_is_dropped(socket_enabled):
    """A row with no id can't be meaningfully tracked -- must be
    filtered out rather than passed through."""
    server = _FakeNexusAudioServer(
        health={"status": "ok", "version": "1.0.0-rc5"},
        sources={"sources": [{"name": "no id here"}]},
    )
    server.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        assert monitor.snapshot()[0]["sources"] == []
    finally:
        server.stop()


async def test_unreachable_gateway_reports_offline_not_a_crash(socket_enabled):
    monitor = NexusAudioMonitor(["127.0.0.1"], port=1, timeout_s=1.0)  # port 1 reserved, always refused on loopback
    await monitor.async_update()
    row = monitor.snapshot()[0]
    assert row["online"] is False
    assert row["error"] is not None


async def test_never_sends_a_post_control_request(socket_enabled):
    """The whole point of this module's narrow scope: it must never
    start/stop/restart a source, reload config, or select an AES67
    session -- guards against a future edit accidentally adding one."""
    server = _FakeNexusAudioServer(
        health={"status": "ok", "version": "1.0.0-rc5"},
        sources={"sources": [_real_source_row()]},
    )
    server.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        for path in server.received_paths:
            assert path in ("/health", "/api/sources")
            assert "/source/start" not in path
            assert "/source/stop" not in path
            assert "/source/restart" not in path
            assert "/reload" not in path
    finally:
        server.stop()


async def test_sources_endpoint_failure_still_reports_health(socket_enabled):
    """/api/sources failing (e.g. a future add-on version renames it)
    must not prevent reporting basic online/version status from
    /health, which succeeded."""
    class _HealthOnlyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"status": "ok", "version": "1.0.0-rc5"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), _HealthOnlyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monitor = NexusAudioMonitor(["127.0.0.1"], port=port)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["version"] == "1.0.0-rc5"
        assert row["sources"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def test_no_hosts_is_a_noop(socket_enabled):
    monitor = NexusAudioMonitor([])
    await monitor.async_update()
    assert monitor.snapshot() == []
