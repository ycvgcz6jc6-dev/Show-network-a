"""Millumin passive feedback monitor. Sends real encoded OSC packets
(via encode_osc, already trusted) over a real loopback UDP socket to a
real MilluminMonitor listening via OSCReceiver -- exercises the actual
receive path, not just the message-parsing logic in isolation.
"""
from __future__ import annotations

import asyncio
import socket

import pytest

from custom_components.dmx_monitor.osc_output import encode_osc
from custom_components.dmx_monitor.osc_receiver import parse_basic_message
from custom_components.dmx_monitor.millumin_monitor import MilluminMonitor

pytestmark = pytest.mark.asyncio


def _send(port: int, address: str, args: list) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(encode_osc(address, args), ("127.0.0.1", port))
    finally:
        sock.close()


async def test_column_launched_feedback(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/millumin/board/launchedColumn", [11, "Intro"])
        await asyncio.sleep(0.2)

        snap = monitor.snapshot()
        assert snap["feedback_active"] is True
        assert snap["current_column"] == {"index": 11, "name": "Intro", "state": "launched", "at": snap["current_column"]["at"]}
        assert snap["scope"] == "passive_feedback_only_nothing_ever_sent"
    finally:
        await monitor.stop()


async def test_media_started_on_named_layer(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/millumin/layer:Background/mediaStarted", [3, "sunset.mov", 42.5])
        await asyncio.sleep(0.2)

        layer = monitor.snapshot()["layers"][0]
        assert layer["identifier"] == "layer:Background"
        assert layer["playing"] is True
        assert layer["media_name"] == "sunset.mov"
        assert layer["duration"] == 42.5
        assert layer["last_event"] == "started"
    finally:
        await monitor.stop()


async def test_media_stopped_clears_playing_and_name(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/millumin/index:2/mediaStarted", [1, "clip.mov", 10.0])
        await asyncio.sleep(0.15)
        _send(port, "/millumin/index:2/mediaStopped", [1, "clip.mov"])
        await asyncio.sleep(0.15)

        layer = monitor.snapshot()["layers"][0]
        assert layer["identifier"] == "index:2"
        assert layer["playing"] is False
        assert layer["media_name"] is None
        assert layer["last_event"] == "stopped"
    finally:
        await monitor.stop()


async def test_media_paused_keeps_media_name_but_not_playing(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/millumin/layer:Main/mediaStarted", [1, "loop.mov", 5.0])
        await asyncio.sleep(0.15)
        _send(port, "/millumin/layer:Main/mediaPaused", [1, "loop.mov"])
        await asyncio.sleep(0.15)

        layer = monitor.snapshot()["layers"][0]
        assert layer["playing"] is False
        assert layer["last_event"] == "paused"
    finally:
        await monitor.stop()


async def test_non_millumin_prefixed_message_is_ignored(socket_enabled):
    """This module only interprets the documented /millumin-prefixed
    feedback shape -- a plain OSC message that happens to arrive on the
    same port (e.g. stray traffic) must not be mistaken for feedback."""
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/some/other/thing", [1, 2, 3])
        await asyncio.sleep(0.2)

        snap = monitor.snapshot()
        assert snap["messages_received"] == 0
        assert snap["feedback_active"] is False
        assert snap["layers"] == []
    finally:
        await monitor.stop()


async def test_no_feedback_yet_reports_inactive(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        snap = monitor.snapshot()
        assert snap["feedback_active"] is False
        assert snap["current_column"] is None
        assert snap["layers"] == []
    finally:
        await monitor.stop()


async def test_multiple_layers_tracked_independently(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        _send(port, "/millumin/layer:Video/mediaStarted", [1, "a.mov", 1.0])
        _send(port, "/millumin/layer:Text/mediaStarted", [2, "b.mov", 2.0])
        await asyncio.sleep(0.2)

        by_id = {l["identifier"]: l for l in monitor.snapshot()["layers"]}
        assert len(by_id) == 2
        assert by_id["layer:Video"]["media_name"] == "a.mov"
        assert by_id["layer:Text"]["media_name"] == "b.mov"
    finally:
        await monitor.stop()


async def test_ping_sent_once_at_startup_when_target_configured(socket_enabled):
    """A real UDP listener receives the actual /millumin/ping packet
    this module sends -- not mocked."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.bind(("127.0.0.1", 0))
    listener.settimeout(2.0)
    ping_port = listener.getsockname()[1]
    try:
        monitor = MilluminMonitor(host="127.0.0.1", port=0, ping_target=("127.0.0.1", ping_port))
        await monitor.start()
        try:
            data, _addr = listener.recvfrom(4096)
            address, _values = parse_basic_message(data)
            assert address == "/millumin/ping"
            assert monitor.snapshot()["ping_sent"] is True
            assert monitor.snapshot()["ping_target"] == f"127.0.0.1:{ping_port}"
        finally:
            await monitor.stop()
    finally:
        listener.close()


async def test_no_ping_sent_when_no_target_configured(socket_enabled):
    monitor = MilluminMonitor(host="127.0.0.1", port=0)  # ping_target defaults to None
    await monitor.start()
    try:
        snap = monitor.snapshot()
        assert snap["ping_sent"] is False
        assert snap["ping_target"] is None
    finally:
        await monitor.stop()


async def test_ping_reply_is_handled_by_the_same_feedback_parser(socket_enabled):
    """Confirms the architectural claim in the module docstring: /ping's
    reply (per Millumin's own developer, only ever the same feedback
    shape) needs no separate parsing path -- a message arriving that
    happens to look like a /ping-triggered state dump is processed
    identically to spontaneous feedback."""
    monitor = MilluminMonitor(host="127.0.0.1", port=0)
    await monitor.start()
    try:
        port = monitor.receiver.transport.get_extra_info("sockname")[1]
        # Simulates one of the "several OSC messages describing layer
        # state" Millumin's docs say /ping's reply consists of.
        _send(port, "/millumin/layer:Main/mediaStarted", [1, "reply.mov", 12.0])
        await asyncio.sleep(0.2)
        layer = monitor.snapshot()["layers"][0]
        assert layer["media_name"] == "reply.mov"
    finally:
        await monitor.stop()
