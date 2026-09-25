"""QLab status monitor. Uses real loopback UDP sockets rather than
mocking the socket layer -- exercises the actual OSC wire encoding
(encode_osc, already trusted) and decoding (parse_basic_message,
already trusted) end to end, against a fake server replying exactly in
the documented /reply/{address} {json_string} shape.
"""
from __future__ import annotations

import asyncio
import json
import socket

import pytest

from custom_components.dmx_monitor.osc_output import encode_osc
from custom_components.dmx_monitor.osc_receiver import parse_basic_message
from custom_components.dmx_monitor.qlab_monitor import QLabMonitor

pytestmark = pytest.mark.asyncio


class _FakeQLabServer:
    """Replies to /version, /workspaces, and /workspace/{id}/thump
    exactly per QLab's documented reply shape: same-named /reply/...
    address, single JSON-string argument."""

    def __init__(self, version="5.6.1", workspaces=None, respond=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        self.version = version
        self.workspaces = workspaces if workspaces is not None else []
        self.respond = respond
        self.received: list[str] = []
        self._task = None

    async def _serve(self):
        loop = asyncio.get_running_loop()
        while True:
            data, addr = await loop.sock_recvfrom(self.sock, 4096)
            address, _values = parse_basic_message(data)
            self.received.append(address)
            if not self.respond:
                continue
            if address == "/version":
                payload = self.version
            elif address == "/workspaces":
                payload = self.workspaces
            elif address.endswith("/thump"):
                payload = "thump"
            else:
                continue
            reply = encode_osc(f"/reply{address}", [json.dumps(payload)])
            await loop.sock_sendto(self.sock, reply, addr)

    def start(self):
        self._task = asyncio.get_running_loop().create_task(self._serve())

    def stop(self):
        if self._task:
            self._task.cancel()
        self.sock.close()


async def test_online_qlab_reports_version_and_workspaces(socket_enabled):
    server = _FakeQLabServer(
        version="5.6.1",
        workspaces=[{"uniqueID": "ABC-123", "displayName": "hamlet", "port": 53000, "udpReplyPort": 53001, "version": "5.6.1"}],
    )
    server.start()
    try:
        monitor = QLabMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()

        rows = monitor.snapshot()
        assert len(rows) == 1
        row = rows[0]
        assert row["online"] is True
        assert row["version"] == "5.6.1"
        assert row["workspace_count"] == 1
        assert row["workspaces"][0]["unique_id"] == "ABC-123"
        assert row["workspaces"][0]["display_name"] == "hamlet"
        assert row["workspaces"][0]["thump_ok"] is True
        assert row["scope"] == "status_only_no_cue_control"
    finally:
        server.stop()


async def test_offline_qlab_reports_not_online_not_a_crash(socket_enabled):
    server = _FakeQLabServer(respond=False)
    server.start()
    try:
        monitor = QLabMonitor(["127.0.0.1"], port=server.port, timeout_s=0.3)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["online"] is False
        assert row["error"] is not None
    finally:
        server.stop()


async def test_no_workspaces_open_still_reports_online(socket_enabled):
    """QLab can be running with zero workspaces open (e.g. just
    launched) -- /version alone should still be enough to report
    online, distinct from workspace-level status."""
    server = _FakeQLabServer(version="5.6.1", workspaces=[])
    server.start()
    try:
        monitor = QLabMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["version"] == "5.6.1"
        assert row["workspace_count"] == 0
    finally:
        server.stop()


async def test_never_sends_a_cue_control_message(socket_enabled):
    """The whole point of this module's narrow scope: it must never send
    /go, /panic, /stop, or anything workspace-control-related -- guards
    against a future edit accidentally adding one."""
    server = _FakeQLabServer(
        version="5.6.1",
        workspaces=[{"uniqueID": "ABC-123", "displayName": "hamlet", "port": 53000}],
    )
    server.start()
    try:
        monitor = QLabMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()

        for address in server.received:
            assert address in ("/version", "/workspaces") or address.endswith("/thump")
            assert "/go" not in address
            assert "/panic" not in address
            assert "/stop" not in address
    finally:
        server.stop()


async def test_unreachable_host_does_not_break_other_hosts(socket_enabled):
    good_server = _FakeQLabServer(version="5.6.1", workspaces=[])
    good_server.start()
    try:
        monitor = QLabMonitor(["127.0.0.1", "192.0.2.5"], port=good_server.port, timeout_s=0.3)
        await monitor.async_update()

        rows = {r["host"]: r for r in monitor.snapshot()}
        assert rows["127.0.0.1"]["online"] is True
        assert rows["192.0.2.5"]["online"] is False
    finally:
        good_server.stop()


async def test_no_hosts_is_a_noop(socket_enabled):
    monitor = QLabMonitor([])
    await monitor.async_update()
    assert monitor.snapshot() == []


async def test_reply_that_is_not_valid_json_is_kept_as_raw_string(socket_enabled):
    """The documented reply argument is "the JSON-encoded result" -- a
    malformed or non-JSON reply from an unexpected QLab version should
    degrade gracefully (kept as-is) rather than crash the poll."""
    server = _FakeQLabServer()
    server.start()

    async def _serve_raw():
        loop = asyncio.get_running_loop()
        while True:
            data, addr = await loop.sock_recvfrom(server.sock, 4096)
            address, _values = parse_basic_message(data)
            if address == "/version":
                reply = encode_osc("/reply/version", ["not-json-just-text"])
                await loop.sock_sendto(server.sock, reply, addr)

    server._task.cancel()
    server._task = asyncio.get_running_loop().create_task(_serve_raw())
    try:
        monitor = QLabMonitor(["127.0.0.1"], port=server.port)
        await monitor.async_update()
        row = monitor.snapshot()[0]
        assert row["online"] is True
        assert row["version"] == "not-json-just-text"
    finally:
        server.stop()
