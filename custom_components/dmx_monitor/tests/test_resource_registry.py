"""Tests for resource_registry.py. No test previously existed for this
module, despite it being the exact code path that caused a real
production issue: "Task could not be canceled and was still running
after shutdown" for show-network-sacn-supervisor and
show-network-artnet-supervisor, confirmed in Home Assistant's own logs
after deploying this project's other 0.15.27 changes. Root cause: no
per-resource timeout at all in async_stop_all -- a single slow resource
stopping could consume the whole of Home Assistant's own overall unload
budget, starving whatever was stopped after it.

Uses real asyncio timing (asyncio.sleep, real timeouts), not mocked
clocks, since the exact regression is about genuine wall-clock
starvation between resources.
"""
from __future__ import annotations

import asyncio
import logging

import pytest

from custom_components.dmx_monitor.resource_registry import (
    ProtocolDriver, ResourceRegistry, RuntimeResource,
)

pytestmark = pytest.mark.asyncio


class _FakeInstance:
    def __init__(self, delay: float = 0.0, raises: Exception | None = None):
        self.delay = delay
        self.raises = raises
        self.stopped = False

    async def stop(self):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raises:
            raise self.raises
        self.stopped = True


class _SyncInstance:
    """Some resources' stop_method is synchronous (no __await__) --
    async_stop already handles this; confirmed still true here."""
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def _resource(resource_id, instance, stop_method="stop"):
    return RuntimeResource(ProtocolDriver(resource_id, "TEST"), resource_id, instance, stop_method)


async def test_all_resources_stopped_when_none_are_slow():
    registry = ResourceRegistry()
    a, b = _FakeInstance(), _FakeInstance()
    registry.add(_resource("a", a))
    registry.add(_resource("b", b))
    await registry.async_stop_all(logging.getLogger("test"))
    assert a.stopped is True
    assert b.stopped is True


async def test_a_slow_resource_does_not_starve_the_next_one():
    """The exact regression: a resource stopped earlier in the sequence
    that takes too long must not prevent a later resource from being
    stopped at all -- it must time out and move on."""
    slow = _FakeInstance(delay=2.0)
    fast = _FakeInstance()
    registry2 = ResourceRegistry()
    registry2.add(_resource("fast", fast))   # stopped 2nd (reverse insertion order)
    registry2.add(_resource("slow", slow))   # stopped 1st (reverse insertion order)

    start = asyncio.get_running_loop().time()
    await registry2.async_stop_all(logging.getLogger("test"), timeout=0.2)
    elapsed = asyncio.get_running_loop().time() - start

    assert fast.stopped is True, "a resource stopped after a slow one must still be stopped"
    assert slow.stopped is False, "the slow one itself did not finish within its timeout"
    assert elapsed < 1.0, "must not have waited for the slow resource's full 2s delay"


async def test_timeout_logs_a_warning_but_continues():
    slow = _FakeInstance(delay=2.0)
    fast = _FakeInstance()
    registry = ResourceRegistry()
    registry.add(_resource("fast", fast))
    registry.add(_resource("slow", slow))

    logger = logging.getLogger("test_timeout_warning")
    messages = []
    logger.warning = lambda *a, **k: messages.append(a[0] % a[1:] if a[1:] else a[0])

    await registry.async_stop_all(logger, timeout=0.2)
    assert any("slow" in m for m in messages)
    assert fast.stopped is True


async def test_exception_during_stop_does_not_abort_the_rest():
    failing = _FakeInstance(raises=RuntimeError("boom"))
    ok = _FakeInstance()
    registry = ResourceRegistry()
    registry.add(_resource("ok", ok))
    registry.add(_resource("failing", failing))
    await registry.async_stop_all(logging.getLogger("test"))
    assert ok.stopped is True  # unaffected by the other resource's exception


async def test_synchronous_stop_method_still_supported():
    instance = _SyncInstance()
    registry = ResourceRegistry()
    registry.add(_resource("sync", instance))
    await registry.async_stop_all(logging.getLogger("test"))
    assert instance.stopped is True


async def test_resources_cleared_after_stop_all():
    registry = ResourceRegistry()
    registry.add(_resource("a", _FakeInstance()))
    await registry.async_stop_all(logging.getLogger("test"))
    assert registry.snapshot() == []


async def test_empty_registry_is_a_noop():
    registry = ResourceRegistry()
    await registry.async_stop_all(logging.getLogger("test"))  # must not raise
