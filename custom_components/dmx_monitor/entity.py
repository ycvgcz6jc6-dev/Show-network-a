"""Base entity for Show Network."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ShowNetworkCoordinator

from .const import DOMAIN


class ShowNetworkEntity(CoordinatorEntity[ShowNetworkCoordinator]):
    """Base entity sharing the coordinator and device metadata."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ShowNetworkCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
