"""Bounded asynchronous flow primitives for high-rate show telemetry.

The receive path stays cheap: one latest value per logical key, bounded memory,
and one asyncio worker.  The same primitive can be used by future output
pipelines (including the dormant Power Manager) without adding Node-RED.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Awaitable, Callable, Generic, Hashable, TypeVar

T = TypeVar("T")


@dataclass
class FlowStats:
    received: int = 0
    coalesced: int = 0
    suppressed: int = 0
    processed: int = 0
    dropped: int = 0
    max_pending: int = 0
    worker_runs: int = 0


class LatestValuePipeline(Generic[T]):
    """Bounded latest-value queue: one pending value per flow key.

    The worker never creates a task per packet.  A burst only updates the
    latest value for an existing key, preventing task/queue amplification.
    """

    def __init__(
        self,
        processor: Callable[[Hashable, T], Awaitable[None]],
        interval_s: float = 0.05,
        max_keys: int = 256,
        byte_change_threshold: int = 1,
    ) -> None:
        self.processor = processor
        self.interval_s = max(0.01, float(interval_s))
        self.max_keys = max(1, int(max_keys))
        self.byte_change_threshold = max(0, int(byte_change_threshold))
        self._pending: dict[Hashable, T] = {}
        self._last: dict[Hashable, T] = {}
        self._key_order: list[Hashable] = []
        self._task: asyncio.Task | None = None
        self._stopping = False
        self.stats = FlowStats()

    @staticmethod
    def _changed_count(old: T | None, new: T) -> int | None:
        if isinstance(old, (bytes, bytearray)) and isinstance(new, (bytes, bytearray)):
            return sum(a != b for a, b in zip(old, new)) + abs(len(old) - len(new))
        return None

    def push_nowait(self, key: Hashable, value: T) -> None:
        if self._stopping:
            return
        self.stats.received += 1
        previous = self._last.get(key)
        changed = self._changed_count(previous, value)
        if changed is not None and changed < self.byte_change_threshold:
            self.stats.suppressed += 1
            return
        if key in self._pending:
            self.stats.coalesced += 1
        elif len(self._pending) >= self.max_keys:
            self.stats.dropped += 1
            return
        self._pending[key] = value
        self.stats.max_pending = max(self.stats.max_pending, len(self._pending))
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="show-network-flow-pipeline")

    async def _worker(self) -> None:
        self.stats.worker_runs += 1
        while self._pending and not self._stopping:
            pending = self._pending
            self._pending = {}
            for key, value in pending.items():
                try:
                    await self.processor(key, value)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.stats.dropped += 1
                else:
                    if key not in self._last:
                        self._key_order.append(key)
                    self._last[key] = value
                    while len(self._last) > self.max_keys and self._key_order:
                        old_key = self._key_order.pop(0)
                        if old_key != key:
                            self._last.pop(old_key, None)
                    self.stats.processed += 1
            if self._pending and not self._stopping:
                await asyncio.sleep(self.interval_s)

    async def async_stop(self) -> None:
        self._stopping = True
        self._pending.clear()
        self._last.clear()
        self._key_order.clear()
        task = self._task
        self._task = None
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def snapshot(self) -> dict[str, int]:
        return self.stats.__dict__.copy()


class AsyncGate:
    """Small cancellation-safe concurrency gate for bounded async polling."""

    def __init__(self, limit: int = 8) -> None:
        self.limit = max(1, int(limit))
        self._semaphore = asyncio.Semaphore(self.limit)

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._semaphore:
            return await operation()
