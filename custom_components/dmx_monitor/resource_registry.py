"""Small driver/resource boundary for Show Network runtime components.

A protocol driver describes *how* a protocol is handled. A runtime resource is
one concrete binding of that driver to an interface/device/session. Keeping the
binding explicit prevents protocol code from becoming coupled to HA lifecycle
or to a particular NIC/device address.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


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

    async def async_stop_all(self, logger) -> None:
        for resource in reversed(list(self._resources.values())):
            try:
                await resource.async_stop()
            except Exception as err:
                logger.debug("Error while stopping resource %s: %s", resource.resource_id, err)
        self._resources.clear()
