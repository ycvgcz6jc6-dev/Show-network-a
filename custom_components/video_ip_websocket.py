"""Authenticated websocket access to Phase 10 supervision data."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api

from . import DOMAIN


@websocket_api.websocket_command({vol.Required("type"): "dmx_monitor/video_ip_supervision"})
@websocket_api.async_response
async def websocket_video_ip_supervision(hass, connection, msg) -> None:
    """Return panel-only video supervision data; no HA entities are needed."""
    entries = hass.data.get(DOMAIN, {})
    snapshots = []
    for entry_id, values in entries.items():
        coordinator = values.get("coordinator") if isinstance(values, dict) else None
        if coordinator is None:
            continue
        data = coordinator.video_ip_supervision.snapshot()
        snapshots.append({"entry_id": entry_id, **data})
    if not snapshots:
        connection.send_result(msg["id"], {
            "mode": "supervision_only", "entities_created": 0,
            "endpoint_count": 0, "online_count": 0, "protocols": {}, "endpoints": [],
        })
        return
    if len(snapshots) == 1:
        connection.send_result(msg["id"], snapshots[0])
        return
    endpoints = []
    protocols = {}
    for snap in snapshots:
        for item in snap.get("endpoints", []):
            endpoints.append({"entry_id": snap["entry_id"], **item})
        for name, count in snap.get("protocols", {}).items():
            protocols[name] = protocols.get(name, 0) + int(count)
    connection.send_result(msg["id"], {
        "mode": "supervision_only", "entities_created": 0,
        "endpoint_count": len(endpoints), "online_count": sum(1 for x in endpoints if x.get("online")),
        "protocols": protocols, "endpoints": endpoints,
    })


def async_register(hass) -> None:
    key = f"{DOMAIN}_video_ip_ws_registered"
    if hass.data.get(key):
        return
    websocket_api.async_register_command(hass, websocket_video_ip_supervision)
    hass.data[key] = True
