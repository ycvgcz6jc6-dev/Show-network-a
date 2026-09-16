"""Uniform lifecycle tracking for every background resource Show Network starts.

__init__.py's async_unload_entry() already prefers this over its own
hardcoded fallback stop-list: "registry = data.get('resource_registry'); if
registry is not None: await registry.async_stop_all(_LOGGER)". This module
is what that registry actually is.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any


class ResourceRegistry:
    def __init__(self) -> None:
        self._items: list[tuple[str, Any, str]] = []

    def register(self, name: str, obj: Any, stop_method: str = "stop") -> None:
        """Track ``obj`` under ``name``; stopped by calling ``obj.<stop_method>()``."""
        if obj is None:
            return
        self._items.append((name, obj, stop_method))

    async def async_stop_all(self, logger: logging.Logger) -> None:
        """Stop every registered resource, most-recently-registered first.

        Never raises: a failure stopping one resource must not prevent the
        rest from being given a chance to stop too.
        """
        for name, obj, stop_method in reversed(self._items):
            method = getattr(obj, stop_method, None)
            if method is None:
                continue
            try:
                result = method()
                if asyncio.iscoroutine(result):
                    await result
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 -- must not abort remaining shutdowns
                logger.debug("Error stopping resource %s: %s", name, err)
        self._items.clear()

    def snapshot(self) -> dict[str, Any]:
        return {"resources": [name for name, _, _ in self._items], "resource_count": len(self._items)}
