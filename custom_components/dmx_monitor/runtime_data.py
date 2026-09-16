"""Typed runtime state for the Show Network config entry."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class ShowNetworkRuntimeData:
    """Objects that live only for the lifetime of one config entry."""
    coordinator: Any
    resource_registry: Any
    archive: Any
    backup_manager: Any
