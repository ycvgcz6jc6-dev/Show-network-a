"""Bounded Home Assistant action sink.

Protocol/runtime code submits normalized actions here; HA service execution is
kept behind one bounded worker with optional per-zone coalescing and pacing.
"""
from __future__ import annotations
import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from ..core.contracts import ServiceAction

@dataclass(frozen=True, slots=True)
class _QueuedAction:
    action: ServiceAction
    zone_id: str | None = None

class HAActionDispatcher:
    def __init__(self, hass: HomeAssistant, archive=None, maxsize: int = 512) -> None:
        self.hass = hass
        self.archive = archive
        self.queue: asyncio.Queue[_QueuedAction | None] = asyncio.Queue(maxsize=maxsize)
        self._zone_pending: dict[str, ServiceAction] = {}
        self._zone_enqueued: set[str] = set()
        self._task: asyncio.Task | None = None
        self.dropped = 0
        self.executed = 0
        self.failed = 0

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = self.hass.async_create_background_task(self._run(), name="show-network-ha-actions")

    def submit(self, action: ServiceAction, *, zone_id: str | None = None) -> bool:
        if zone_id:
            self._zone_pending[zone_id] = action
            if zone_id in self._zone_enqueued:
                return True
            self._zone_enqueued.add(zone_id)
            queued = _QueuedAction(action, zone_id)
        else:
            queued = _QueuedAction(action)
        try:
            self.queue.put_nowait(queued)
            return True
        except asyncio.QueueFull:
            if zone_id:
                self._zone_enqueued.discard(zone_id)
            self.dropped += 1
            return False

    async def _run(self) -> None:
        last_dispatch = 0.0
        while True:
            item = await self.queue.get()
            try:
                if item is None:
                    return
                action = item.action
                if item.zone_id:
                    zone_id = item.zone_id
                    action = self._zone_pending.pop(zone_id, action)
                    self._zone_enqueued.discard(zone_id)
                if not self.hass.services.has_service(action.domain, action.service):
                    self.failed += 1
                    continue
                if action.rate_limit_hz:
                    interval = 1.0 / max(0.1, float(action.rate_limit_hz))
                    wait = interval - (time.monotonic() - last_dispatch)
                    if wait > 0:
                        await asyncio.sleep(wait)
                await self.hass.services.async_call(action.domain, action.service, dict(action.data), blocking=False)
                last_dispatch = time.monotonic()
                self.executed += 1
                if self.archive:
                    self.archive.record("system", "ha_action_executed", {"origin": action.origin, "domain": action.domain, "service": action.service, "entity_id": action.data.get("entity_id")})
            except (HomeAssistantError, ValueError, TypeError) as err:
                self.failed += 1
                if self.archive and item is not None:
                    self.archive.record("system", "ha_action_failed", {"origin": item.action.origin, "reason": str(err), "domain": item.action.domain, "service": item.action.service})
            finally:
                self.queue.task_done()

    async def async_stop(self) -> None:
        task = self._task
        self._task = None
        self._zone_pending.clear()
        self._zone_enqueued.clear()
        if task and not task.done():
            with suppress(asyncio.QueueFull):
                self.queue.put_nowait(None)
            if not task.done():
                task.cancel() if self.queue.full() else None
            await asyncio.gather(task, return_exceptions=True)

    def snapshot(self) -> dict[str, int]:
        return {"queued": self.queue.qsize(), "dropped": self.dropped, "executed": self.executed, "failed": self.failed}
