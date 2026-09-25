"""Audit-confirmed: a CancelledError during a Show Network reload traced
back to runtime/setup.py -> coordinator.py -> PJLinkMonitor.async_update(),
which used to await a mandatory 10.5s PJLink broadcast discovery inline on
the coordinator's very first refresh -- the same class of bug already
fixed for vendor discovery ("previously blocking async_setup_entry
directly, contributing to slow/timed-out config entry bootstraps").
"""
from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from custom_components.dmx_monitor import projector_monitor as projector_monitor_module
from custom_components.dmx_monitor.projector_monitor import PJLinkMonitor

pytestmark = pytest.mark.asyncio


async def test_first_discovery_does_not_block_async_update(monkeypatch):
    monitor = PJLinkMonitor()

    # A short-lived, test-scoped executor rather than the module's shared,
    # deliberately long-lived _PROJECTOR_EXECUTOR: this test's harness
    # (pytest-homeassistant-custom-component) asserts no non-daemon
    # threads survive a test, and that shared pool is meant to outlive any
    # single call by design (reused across every discovery/poll in
    # production). Explicitly shutting it down here keeps that assertion
    # meaningful without touching the pool other tests/production rely on.
    temp_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test_projector")
    monkeypatch.setattr(projector_monitor_module, "_PROJECTOR_EXECUTOR", temp_executor)

    # Stand in for the real UDP broadcast sweep: sleeps far longer than a
    # reasonable async_update() call should ever take, so the test fails
    # loudly if the discovery is still being awaited inline.
    def slow_discover_sync(timeout):
        time.sleep(0.5)
        return [{"host": "10.4.1.30", "mac": "aa:bb:cc:dd:ee:ff", "interface": "10.4.1.8"}]

    monkeypatch.setattr(monitor, "_discover_sync", slow_discover_sync)

    try:
        started = time.monotonic()
        await monitor.async_update()
        elapsed = time.monotonic() - started

        assert elapsed < 0.3, (
            f"async_update() took {elapsed:.2f}s on first call -- the discovery "
            "sweep is still blocking it inline instead of running in the background"
        )
        # Nothing discovered *yet* -- the background sweep is still in flight.
        assert monitor.last_discovery_monotonic is None

        # Let the background task actually finish.
        await asyncio.sleep(0.7)
        assert monitor.last_discovery_monotonic is not None
        assert any(r.host == "10.4.1.30" for r in monitor.records)
    finally:
        temp_executor.shutdown(wait=True)


async def test_second_call_before_first_discovery_finishes_does_not_duplicate_it(monkeypatch):
    monitor = PJLinkMonitor()
    call_count = 0

    temp_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test_projector2")
    monkeypatch.setattr(projector_monitor_module, "_PROJECTOR_EXECUTOR", temp_executor)

    def slow_discover_sync(timeout):
        nonlocal call_count
        call_count += 1
        time.sleep(0.3)
        return []

    monkeypatch.setattr(monitor, "_discover_sync", slow_discover_sync)

    try:
        await monitor.async_update()
        await monitor.async_update()  # fires before the first background sweep finishes
        await asyncio.sleep(0.5)

        assert call_count == 1, "a second async_update() call while discovery is in flight must not start a duplicate sweep"
    finally:
        temp_executor.shutdown(wait=True)


async def test_async_stop_cancels_in_flight_background_discovery(monkeypatch):
    """Lifecycle audit (Phase C2): the background task async_update() now
    creates for the first discovery is exactly why PJLinkMonitor needs its
    own async_stop() -- before that fix it never owned anything that
    outlived a single call, so a reload/unload had nothing to leak.
    Registered as a stoppable resource in runtime/setup.py; this test
    covers the class's own half of that contract.
    """
    monitor = PJLinkMonitor()

    temp_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test_projector3")
    monkeypatch.setattr(projector_monitor_module, "_PROJECTOR_EXECUTOR", temp_executor)

    def slow_discover_sync(timeout):
        time.sleep(2.0)  # long enough that the test would hang if not cancelled
        return []

    monkeypatch.setattr(monitor, "_discover_sync", slow_discover_sync)

    try:
        await monitor.async_update()  # starts the background discovery task
        assert monitor._discovery_task is not None
        assert not monitor._discovery_task.done()

        started = time.monotonic()
        await monitor.async_stop()
        elapsed = time.monotonic() - started

        assert elapsed < 0.5, f"async_stop() took {elapsed:.2f}s -- it should cancel, not wait out the sweep"
        assert monitor._discovery_task.cancelled() or monitor._discovery_task.done()

        # Calling it again with nothing in flight must be a safe no-op.
        await monitor.async_stop()
    finally:
        temp_executor.shutdown(wait=True)


async def test_periodic_rediscovery_after_first_run_still_awaits_inline(monkeypatch):
    """Once last_discovery_monotonic is set, the >300s periodic re-scan
    path is unchanged -- only the very first, setup-time discovery is
    deferred to the background."""
    monitor = PJLinkMonitor()
    monitor.last_discovery_monotonic = time.monotonic() - 301

    called_with = []

    async def fake_async_discover(timeout=10.5):
        called_with.append(timeout)
        monitor.last_discovery_monotonic = time.monotonic()
        return 0

    monkeypatch.setattr(monitor, "async_discover", fake_async_discover)
    await monitor.async_update()

    assert called_with == [10.5], "periodic re-discovery past 300s should still be awaited directly"
