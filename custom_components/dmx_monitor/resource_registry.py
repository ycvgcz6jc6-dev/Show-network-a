"""Small driver/resource boundary for Show Network runtime components.

A protocol driver describes *how* a protocol is handled. A runtime resource is
one concrete binding of that driver to an interface/device/session. Keeping the
binding explicit prevents protocol code from becoming coupled to HA lifecycle
or to a particular NIC/device address.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

# Audit fix (confirmed in production logs after 0.15.27 deployment):
# "Task could not be canceled and was still running after shutdown" for
# show-network-sacn-supervisor and show-network-artnet-supervisor.
# Root cause traced to async_stop_all below, not to those tasks'
# own cancellation handling (DmxNetworkReceiver.stop() awaits its own
# tasks correctly) -- every resource was stopped sequentially with no
# per-resource time budget at all. This project has grown many more
# stoppable resources over this session (Millumin, Green-GO, and others,
# each with their own socket/listener to tear down); a single slow or
# genuinely stuck resource earlier in the sequence could consume the
# whole of Home Assistant's own overall unload timeout, starving
# whichever resources happened to be stopped later -- which is exactly
# the "some tasks, not all" shape the production warning showed.
_STOP_TIMEOUT_S = 5.0


@dataclass(frozen=True, slots=True)
class ProtocolDriver:
    key: str
    category: str
    description: str = ""


@dataclass(slots=True)
class RuntimeResource:
    driver: ProtocolDriver
    resource_id: str
    instance: Any
    stop_method: str = "stop"
    metadata: dict[str, Any] | None = None

    async def async_stop(self) -> None:
        method: Callable[[], Awaitable[None] | None] = getattr(self.instance, self.stop_method)
        result = method()
        if hasattr(result, "__await__"):
            await result


class ResourceRegistry:
    """Own active protocol resources for one config entry."""

    def __init__(self) -> None:
        self._resources: dict[str, RuntimeResource] = {}

    def add(self, resource: RuntimeResource) -> None:
        self._resources[resource.resource_id] = resource

    def remove(self, resource_id: str) -> None:
        self._resources.pop(resource_id, None)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "id": resource.resource_id,
                "driver": resource.driver.key,
                "category": resource.driver.category,
                "metadata": resource.metadata or {},
            }
            for resource in self._resources.values()
        ]

    async def async_stop_all(self, logger: logging.Logger, *, timeout: float = _STOP_TIMEOUT_S) -> None:
        for resource in reversed(list(self._resources.values())):
            try:
                await asyncio.wait_for(resource.async_stop(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    "Show Network: %s (%s) did not stop within %.0fs -- moving on so it "
                    "doesn't hold up the rest of shutdown; its own task may still be "
                    "cancelled by Home Assistant's own final cleanup afterwards",
                    resource.resource_id, resource.driver.key, timeout,
                )
            except Exception as err:
                logger.debug("Error while stopping resource %s: %s", resource.resource_id, err)
        self._resources.clear()
