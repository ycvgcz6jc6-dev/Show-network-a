"""Passive Green-GO UDP 5810 multicast monitor. Uses real loopback
multicast sockets (not mocked) -- exercises the actual join/receive
path, not just the surrounding counting logic.
"""
from __future__ import annotations

import asyncio
import socket

import pytest

from custom_components.dmx_monitor.greengo_monitor import GreenGOMonitor, GREENGO_PORT

pytestmark = pytest.mark.asyncio

TEST_GROUP = "239.192.5.81"  # an arbitrary, unused local-admin multicast address for these tests


def _send_multicast(group: str, port: int, payload: bytes) -> None:
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    try:
        sender.sendto(payload, (group, port))
    finally:
        sender.close()


async def test_receives_real_multicast_packets_and_counts_sources(socket_enabled):
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    try:
        _send_multicast(TEST_GROUP, GREENGO_PORT, b"\x01\x02\x03")
        await asyncio.sleep(0.2)  # let the background receive task actually run

        snap = monitor.snapshot()
        assert snap["greengo_packets"] == 1
        assert snap["greengo_sources"] == 1
        assert snap["greengo_multicast_group"] == TEST_GROUP
        assert snap["greengo_scope"] == "presence_only_no_payload_decoded"
        assert snap["greengo_last_seen"] is not None
    finally:
        await monitor.stop()


async def test_never_decodes_or_stores_payload_content(socket_enabled):
    """The whole point of the module's scope: presence only. A payload
    containing something that looks like a channel/level command must
    never surface anywhere in the snapshot -- guards against a future
    edit accidentally starting to parse and expose message content this
    project has no verified spec for."""
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    try:
        _send_multicast(TEST_GROUP, GREENGO_PORT, b"MIXER:Talk/Channel/5 1")
        await asyncio.sleep(0.2)

        snap = monitor.snapshot()
        assert snap["greengo_packets"] == 1
        serialized = str(snap)
        assert "MIXER" not in serialized
        assert "Talk" not in serialized
    finally:
        await monitor.stop()


async def test_multiple_packets_from_same_source_accumulate(socket_enabled):
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    try:
        for _ in range(3):
            _send_multicast(TEST_GROUP, GREENGO_PORT, b"\x00")
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.2)

        snap = monitor.snapshot()
        assert snap["greengo_packets"] == 3
        assert snap["greengo_sources"] == 1  # same loopback source each time
        assert snap["greengo_source_stats"][0]["packets"] == 3
        assert snap["greengo_fresh_sources"] == 1
    finally:
        await monitor.stop()


async def test_no_packets_yet_gives_empty_not_an_error(socket_enabled):
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    try:
        snap = monitor.snapshot()
        assert snap["greengo_packets"] == 0
        assert snap["greengo_sources"] == 0
        assert snap["greengo_source_stats"] == []
        assert snap["greengo_last_seen"] is None
    finally:
        await monitor.stop()


async def test_stop_cancels_task_and_closes_socket_cleanly(socket_enabled):
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    assert monitor._task is not None
    assert monitor._socket is not None
    await monitor.stop()
    assert monitor._task is None
    assert monitor._socket is None


async def test_start_is_idempotent(socket_enabled):
    """Calling start() twice must not open a second socket/task on the
    same port (which would raise "address already in use")."""
    monitor = GreenGOMonitor(TEST_GROUP)
    await monitor.start()
    try:
        await monitor.start()  # must be a no-op, not raise
        first_task = monitor._task
        await monitor.start()
        assert monitor._task is first_task
    finally:
        await monitor.stop()
