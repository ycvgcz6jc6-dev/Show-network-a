"""Shared Home Assistant service helpers."""
from __future__ import annotations
from homeassistant.core import HomeAssistant
from ..const import DOMAIN

def coordinator_for_call(hass: HomeAssistant, call):
    """Resolve a coordinator without assuming the first configured entry."""
    entry_id = call.data.get("entry_id")
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        item = entries.get(str(entry_id))
        if item and item.get("coordinator"):
            return item["coordinator"]
        raise ValueError(f"Unknown config entry: {entry_id}")
    coordinators = [item.get("coordinator") for item in entries.values() if item.get("coordinator")]
    if len(coordinators) == 1:
        return coordinators[0]
    raise ValueError("entry_id is required when multiple DMX Monitor entries are configured")
