"""Tests for the stream duration/idle-timeout logic in video_ip_preview.py.

Covers audit Z-08: the preview stream previously had no maximum duration
and no idle timeout, so a forgotten-open tab or a stalled source could
keep an ffmpeg process running indefinitely.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from custom_components.dmx_monitor.video_ip_preview import stream_preview_frames


class _FakeStdout:
    def __init__(self, chunks, stall_after=None):
        self.chunks = list(chunks)
        self.stall_after = stall_after
        self.reads = 0

    async def read(self, n):
        self.reads += 1
        if self.stall_after is not None and self.reads > self.stall_after:
            await asyncio.sleep(1000)  # simulates a hung/stalled read
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


class _InfiniteStdout:
    async def read(self, n):
        await asyncio.sleep(0.05)
        return b"X" * 100


@pytest.mark.asyncio
async def test_normal_stream_reaches_eof_cleanly():
    written = []

    async def write(chunk):
        written.append(chunk)

    summary = await stream_preview_frames(_FakeStdout([b"a", b"b", b"c"]), write, max_session_s=10, idle_timeout_s=5)
    assert summary["stop_reason"] == "eof"
    assert summary["chunks_sent"] == 3
    assert written == [b"a", b"b", b"c"]


@pytest.mark.asyncio
async def test_stalled_source_stops_via_idle_timeout_quickly():
    async def write(chunk):
        pass

    stdout = _FakeStdout([b"a", b"b", b"c", b"d"], stall_after=2)
    start = time.monotonic()
    summary = await stream_preview_frames(stdout, write, max_session_s=30, idle_timeout_s=0.3)
    elapsed = time.monotonic() - start

    assert summary["stop_reason"] == "idle_timeout"
    assert elapsed < 2.0  # must not hang anywhere near the fake 1000s stall


@pytest.mark.asyncio
async def test_never_ending_source_is_cut_off_at_max_duration():
    async def write(chunk):
        pass

    start = time.monotonic()
    summary = await stream_preview_frames(_InfiniteStdout(), write, max_session_s=0.3, idle_timeout_s=5)
    elapsed = time.monotonic() - start

    assert summary["stop_reason"] == "max_session_duration"
    assert elapsed < 1.0
