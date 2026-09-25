"""Small asyncio-safe coalescing rate limiter for high-frequency telemetry."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Any, Awaitable, Callable


@dataclass
class RateLimitStats:
    received: int = 0
    sent: int = 0
    suppressed_deadband: int = 0
    coalesced: int = 0
    dropped: int = 0


class RateLimiter:
    """Coalesce bursts into at most one callback per interval.

    ``push_nowait`` is intended for synchronous packet callbacks running on the
    Home Assistant event loop. It never awaits and creates at most one worker
    task for an active burst, so 40-50 Hz DMX traffic does not create one task
    per packet.
    """

    def __init__(self, interval_s: float = 0.05, deadband: float = 0.0) -> None:
        self.interval = max(0.01, float(interval_s))
        self.deadband = max(0.0, float(deadband))
        self.stats = RateLimitStats()
        self._last_value: Any = None
        self._pending: Any = None
        self._task: asyncio.Task | None = None
        self._send: Callable[[Any], Awaitable[None]] | None = None
        self._last_sent = 0.0
        self._stopping = False

    def push_nowait(self, value: Any, send: Callable[[Any], Awaitable[None]]) -> None:
        if self._stopping:
            return
        self.stats.received += 1
        self._send = send
        if isinstance(value, (int, float)) and isinstance(self._last_value, (int, float)):
            if abs(value - self._last_value) < self.deadband:
                self.stats.suppressed_deadband += 1
                return
        if self._pending is not None:
            self.stats.coalesced += 1
        self._pending = value
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="show-network-rate-limiter")

    async def push(self, value: Any, send: Callable[[Any], Awaitable[None]]) -> None:
        self.push_nowait(value, send)

    async def _worker(self) -> None:
        while self._pending is not None and not self._stopping:
            wait = self.interval - (monotonic() - self._last_sent)
            if wait > 0:
                await asyncio.sleep(wait)
            value = self._pending
            self._pending = None
            sender = self._send
            if sender is not None:
                try:
                    await sender(value)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Telemetry publishing must never break the packet receiver.
                    self.stats.dropped += 1
                else:
                    self.stats.sent += 1
                    self._last_value = value
                    self._last_sent = monotonic()

    async def async_stop(self) -> None:
        self._stopping = True
        self._pending = None
        task = self._task
        self._task = None
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def snapshot(self) -> dict[str, int]:
        return self.stats.__dict__.copy()
