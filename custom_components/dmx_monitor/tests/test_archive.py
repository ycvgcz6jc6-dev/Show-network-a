"""Tests for custom_components/dmx_monitor/archive.py.

Covers the audit-driven fixes: a genuine global size quota (not just a
per-file rotation threshold), a cap on retained ZIP exports, unique
rotation filenames even for two rotations within the same second, and
counters/logging for previously-silent failures (queue overflow, write
errors, rotation errors).
"""
from __future__ import annotations

import asyncio
import tempfile
import time

import pytest

from custom_components.dmx_monitor.archive import EventArchive, MAX_ZIP_EXPORTS, PER_FILE_ROTATE_BYTES


def test_status_reports_split_and_total_sizes():
    with tempfile.TemporaryDirectory() as tmp:
        archive = EventArchive(tmp, retention_days=30, max_bytes=200_000, destination="test_status")
        archive.root.mkdir(parents=True, exist_ok=True)
        (archive.root / "a.jsonl").write_bytes(b"X" * 1000)
        (archive.root / "show_network_journal_20260101T000000Z.zip").write_bytes(b"Y" * 2000)

        status = archive.status()
        assert status["bytes_jsonl"] == 1000
        assert status["bytes_zip"] == 2000
        assert status["bytes_total"] == 3000
        assert status["over_limit"] is False


def test_global_quota_purges_oldest_files_first():
    with tempfile.TemporaryDirectory() as tmp:
        archive = EventArchive(tmp, retention_days=90, max_bytes=100_000, destination="test_quota")
        archive.root.mkdir(parents=True, exist_ok=True)

        paths = []
        for i in range(5):
            p = archive.root / f"category{i}.jsonl"
            p.write_bytes(b"Z" * 30_000)  # 5 * 30KB = 150KB, over the 100KB quota
            mtime = time.time() - (5 - i) * 60  # category0 oldest, category4 newest
            import os
            os.utime(p, (mtime, mtime))
            paths.append(p)

        archive.cleanup()

        remaining = {p.name for p in archive.root.glob("*.jsonl")}
        total_after = sum(p.stat().st_size for p in archive.root.glob("*.jsonl"))
        assert total_after <= archive.max_bytes
        assert "category0.jsonl" not in remaining  # oldest purged first
        assert "category4.jsonl" in remaining  # newest survives


def test_zip_export_count_is_capped_regardless_of_age():
    with tempfile.TemporaryDirectory() as tmp:
        archive = EventArchive(tmp, retention_days=30, max_bytes=1_000_000, destination="test_zip_cap")
        archive.root.mkdir(parents=True, exist_ok=True)
        import os
        for i in range(12):
            p = archive.root / f"show_network_journal_2026010{i:01d}T000000Z.zip"
            p.write_bytes(b"X" * 1000)
            os.utime(p, (time.time() - (12 - i) * 3600, time.time() - (12 - i) * 3600))

        archive.cleanup()

        remaining = list(archive.root.glob("*.zip"))
        assert len(remaining) <= MAX_ZIP_EXPORTS


@pytest.mark.asyncio
async def test_queue_overflow_is_counted_and_recorded_not_silent():
    with tempfile.TemporaryDirectory() as tmp:
        archive = EventArchive(tmp, retention_days=30, max_bytes=5_000_000, destination="test_overflow")
        archive.root.mkdir(parents=True, exist_ok=True)
        archive._queue = asyncio.Queue(maxsize=2)
        # A running-but-never-draining worker, so the queue genuinely fills up.
        archive._worker = asyncio.create_task(asyncio.sleep(1000))
        try:
            for i in range(2):
                archive.record("test", f"event{i}", {})
            assert archive._dropped_events == 0

            archive.record("test", "overflow", {})  # queue is now full
            assert archive._dropped_events == 1
            assert archive._last_error is not None
            assert "saturated" in archive._last_error

            status = archive.status()
            assert status["dropped_events"] == 1
        finally:
            archive._worker.cancel()


def test_rotation_never_overwrites_a_colliding_filename():
    with tempfile.TemporaryDirectory() as tmp:
        archive = EventArchive(tmp, retention_days=30, max_bytes=5_000_000, destination="test_collision")
        archive.root.mkdir(parents=True, exist_ok=True)

        p = archive.root / "collision.jsonl"
        p.write_bytes(b"X" * (PER_FILE_ROTATE_BYTES + 1))

        import datetime as dtmod
        import unittest.mock as mock

        stamp = dtmod.datetime.now(dtmod.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        collide_path = archive.root / f"collision.{stamp}.jsonl"
        collide_path.write_bytes(b"PRE-EXISTING-DATA")

        class FixedDatetime(dtmod.datetime):
            @classmethod
            def now(cls, tz=None):
                return dtmod.datetime.strptime(stamp, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=tz)

        with mock.patch("custom_components.dmx_monitor.archive.datetime", FixedDatetime):
            archive._rotate(p)

        # The pre-existing file at the exact same timestamp must survive
        # untouched; the new rotation must land under a different name.
        assert collide_path.read_bytes() == b"PRE-EXISTING-DATA"
        rotated = list(archive.root.glob("collision.*.jsonl"))
        assert len(rotated) == 2
