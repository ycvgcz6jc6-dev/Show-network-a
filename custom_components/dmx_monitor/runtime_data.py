"""Typed container stored on ``ConfigEntry.runtime_data``.

Home Assistant's modern integration pattern stores everything a config entry
needs at runtime on ``entry.runtime_data`` instead of ``hass.data[DOMAIN]``.
This dataclass is deliberately thin: it only holds references assembled once
by ``runtime.setup.async_setup_runtime`` and read back by the platform
modules (``sensor.py``, ``binary_sensor.py``, ``switch.py``, ``number.py``,
``scene.py``) when they set up their entities for this entry.

Nothing here owns any network resource itself; lifecycle (start/stop) stays
with ``coordinator`` and ``resource_registry``, matching how
``async_unload_entry`` in ``__init__.py`` stops things via
``data.get("resource_registry")`` / ``coordinator`` rather than via this
container.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .archive import EventArchive
    from .backup import ConfigBackupManager
    from .coordinator import ShowNetworkCoordinator


@dataclass(slots=True)
class ShowNetworkRuntimeData:
    """Everything a Show Network config entry needs at runtime.

    Attributes:
        coordinator: the central ``ShowNetworkCoordinator`` for this entry.
        resource_registry: tracks every started background resource
            (listeners, monitors, workers) so they can all be stopped
            uniformly on unload; may be ``None`` if construction failed
            before the registry was created.
        archive: the persistent Show Timeline / journal archive for this
            entry, or ``None`` if archiving is disabled in options.
        backup_manager: handles Show Network configuration backup/restore
            for this entry, or ``None`` if not yet initialized.
    """

    coordinator: "ShowNetworkCoordinator"
    resource_registry: object | None = None
    archive: "EventArchive | None" = None
    backup_manager: "ConfigBackupManager | None" = None
