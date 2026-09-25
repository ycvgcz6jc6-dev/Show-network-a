"""Yamaha DM3/DM7/Rivage PM scene status monitor. Uses real loopback UDP
sockets (127.0.0.1) rather than mocking the socket layer -- this
exercises the actual OSC wire encoding (encode_osc, already trusted
elsewhere) and decoding (parse_basic_message, already trusted
elsewhere) end to end, not just the surrounding logic.
"""
from __future__ import annotations

import asyncio
import socket

import pytest

from custom_components.dmx_monitor.osc_output import encode_osc
from custom_components.dmx_monitor.yamaha_osc_monitor import YamahaOSCMonitor, YOSC_PORT

pytestmark = pytest.mark.asyncio


class _FakeYOSCServer:
    """Replies to a sscurrentt_ex query on a loopback UDP socket exactly
    the way a real DM7 would, per the official OSC spec's Snapshot
    table: same address echoed back, single string argument with the
    current scene number."""

    def __init__(self, scene_a="3.00", scene_b="1.00", respond=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        self.scene_a = scene_a
        self.scene_b = scene_b
        self.respond = respond
        self.received: list[bytes] = []
        self._task = None

    async def _serve(self):
        loop = asyncio.get_running_loop()
        while True:
            data, addr = await loop.sock_recvfrom(self.sock, 4096)
            self.received.append(data)
            if not self.respond:
                continue
            from custom_components.dmx_monitor.osc_receiver import parse_basic_message
            _address, values = parse_basic_message(data)
            scene_list = values[0] if values else ""
            reply_value = self.scene_a if scene_list == "scene_a" else self.scene_b
            reply = encode_osc("/yosc:req/sscurrentt_ex", [reply_value])
            await loop.sock_sendto(self.sock, reply, addr)

    def start(self):
        self._task = asyncio.get_running_loop().create_task(self._serve())

    def stop(self):
        if self._task:
            self._task.cancel()
        self.sock.close()


async def test_query_round_trip_real_udp_wire_format(socket_enabled):
    server = _FakeYOSCServer(scene_a="4.00", scene_b="2.00")
    server.start()
    try:
        monitor = YamahaOSCMonitor({"127.0.0.1": "DM7 FOH"})
        monitor.__class__  # sanity
        import custom_components.dmx_monitor.yamaha_osc_monitor as yosc_mod
        original_port = yosc_mod.YOSC_PORT
        yosc_mod.YOSC_PORT = server.port
        try:
            await monitor.async_update()
        finally:
            yosc_mod.YOSC_PORT = original_port

        rows = monitor.snapshot()
        assert len(rows) == 1
        row = rows[0]
        assert row["online"] is True
        assert row["scene_a_current"] == "4.00"
        assert row["scene_b_current"] == "2.00"
        assert row["name"] == "DM7 FOH"
        assert row["scope"] == "scene_status_only"

        # Confirm the actual wire request matches the officially
        # documented address/argument shape, not just that *some*
        # request arrived.
        assert len(server.received) == 2  # scene_a, then scene_b
        for packet in server.received:
            from custom_components.dmx_monitor.osc_receiver import parse_basic_message
            address, values = parse_basic_message(packet)
            assert address == "/yosc:req/sscurrentt_ex"
            assert values[0] in ("scene_a", "scene_b")
    finally:
        server.stop()


async def test_no_response_reports_offline_not_a_crash(socket_enabled):
    server = _FakeYOSCServer(respond=False)
    server.start()
    try:
        monitor = YamahaOSCMonitor({"127.0.0.1": "Silent Desk"}, timeout_s=0.3)
        import custom_components.dmx_monitor.yamaha_osc_monitor as yosc_mod
        original_port = yosc_mod.YOSC_PORT
        yosc_mod.YOSC_PORT = server.port
        try:
            await monitor.async_update()
        finally:
            yosc_mod.YOSC_PORT = original_port

        row = monitor.snapshot()[0]
        assert row["online"] is False
        assert row["error"] is not None
        assert "TimeoutError" in row["error"]
    finally:
        server.stop()


async def test_unreachable_host_does_not_crash_or_block_others(socket_enabled):
    good_server = _FakeYOSCServer(scene_a="9.00", scene_b="1.00")
    good_server.start()
    try:
        import custom_components.dmx_monitor.yamaha_osc_monitor as yosc_mod
        original_port = yosc_mod.YOSC_PORT
        yosc_mod.YOSC_PORT = good_server.port
        # 192.0.2.0/24 (TEST-NET-1) is IANA-reserved for documentation and
        # never routable -- a real send will simply go nowhere and the
        # query will time out, exercising genuine failure isolation
        # rather than a mocked exception.
        monitor = YamahaOSCMonitor(
            {"127.0.0.1": "Reachable Desk", "192.0.2.1": "Unreachable Desk"},
            timeout_s=0.3,
        )
        try:
            await monitor.async_update()
        finally:
            yosc_mod.YOSC_PORT = original_port

        rows = {r["host"]: r for r in monitor.snapshot()}
        assert rows["127.0.0.1"]["online"] is True
        assert rows["127.0.0.1"]["scene_a_current"] == "9.00"
        assert rows["192.0.2.1"]["online"] is False
        assert rows["192.0.2.1"]["error"] is not None
    finally:
        good_server.stop()


async def test_no_hosts_is_a_noop():
    monitor = YamahaOSCMonitor({})
    await monitor.async_update()
    assert monitor.snapshot() == []


async def test_never_sends_a_set_or_control_action(socket_enabled):
    """The whole point of this module's narrow scope: it must never send
    anything other than the documented read-only sscurrentt_ex query --
    guards against a future edit accidentally adding a /set call."""
    server = _FakeYOSCServer()
    server.start()
    try:
        import custom_components.dmx_monitor.yamaha_osc_monitor as yosc_mod
        original_port = yosc_mod.YOSC_PORT
        yosc_mod.YOSC_PORT = server.port
        monitor = YamahaOSCMonitor({"127.0.0.1": "Desk"})
        try:
            await monitor.async_update()
        finally:
            yosc_mod.YOSC_PORT = original_port

        from custom_components.dmx_monitor.osc_receiver import parse_basic_message
        for packet in server.received:
            address, _values = parse_basic_message(packet)
            assert address == "/yosc:req/sscurrentt_ex"
            assert "/set" not in address
            assert "/event" not in address
    finally:
        server.stop()
