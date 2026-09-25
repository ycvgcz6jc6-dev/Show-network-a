"""Authenticated, paginated websocket access to the full device inventory.

Completes the audit fix in sensor.py: entity attributes are now always
bounded to stay under Home Assistant Recorder's 16384-byte limit (see
_bounded_attributes), which means a large device_inventory would otherwise
just show a "too large, truncated" summary with no way to see the detail.
This command is that "way to see the detail" -- paginated so even a very
large inventory never sends an unbounded payload over the websocket either.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api

from . import DOMAIN

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@websocket_api.websocket_command({
    vol.Required("type"): "dmx_monitor/device_inventory",
    vol.Optional("entry_id"): str,
    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("limit", default=_DEFAULT_LIMIT): vol.All(vol.Coerce(int), vol.Range(min=1, max=_MAX_LIMIT)),
    vol.Optional("search"): str,
})
@websocket_api.async_response
async def websocket_device_inventory(hass, connection, msg) -> None:
    entries = hass.data.get(DOMAIN, {})
    entry_id = msg.get("entry_id")
    coordinator = None
    if entry_id:
        values = entries.get(entry_id)
        coordinator = values.get("coordinator") if isinstance(values, dict) else None
    else:
        candidates = [v.get("coordinator") for v in entries.values() if isinstance(v, dict) and v.get("coordinator")]
        if len(candidates) == 1:
            coordinator = candidates[0]

    if coordinator is None:
        connection.send_result(msg["id"], {
            "total": 0, "offset": msg["offset"], "limit": msg["limit"], "devices": [],
            "error": "Missing or ambiguous entry_id (multiple Show Network entries exist)" if not entry_id else None,
        })
        return

    rows = list(coordinator.data.get("device_inventory", []))
    search = (msg.get("search") or "").strip().lower()
    if search:
        def matches(row: dict) -> bool:
            haystack = " ".join(str(row.get(k) or "") for k in (
                "display_name", "display_manufacturer", "display_model", "ip", "hostname", "mac", "serial"
            )).lower()
            return search in haystack
        rows = [r for r in rows if matches(r)]

    total = len(rows)
    offset = msg["offset"]
    limit = msg["limit"]
    page = rows[offset:offset + limit]

    connection.send_result(msg["id"], {
        "total": total,
        "offset": offset,
        "limit": limit,
        "devices": page,
    })


def async_register(hass) -> None:
    key = f"{DOMAIN}_device_inventory_ws_registered"
    if hass.data.get(key):
        return
    websocket_api.async_register_command(hass, websocket_device_inventory)
    hass.data[key] = True
