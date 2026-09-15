"""Authenticated, cached CEM3 circuit details outside HA Recorder attributes."""
from __future__ import annotations
import voluptuous as vol
from homeassistant.components import websocket_api
from .const import DOMAIN


@websocket_api.websocket_command({vol.Required('type'): 'dmx_monitor/cem3'})
@websocket_api.async_response
async def websocket_cem3(hass, connection, msg):
    racks, sources, status = [], [], []
    for entry_id, values in hass.data.get(DOMAIN, {}).items():
        coordinator = values.get('coordinator') if isinstance(values, dict) else None
        monitor = getattr(coordinator, 'etc_cem3_monitor', None)
        if monitor is None:
            continue
        snap = monitor.snapshot()
        racks.extend(dict(rack, entry_id=entry_id) for rack in snap['racks'])
        sources.extend(snap['source_ips'])
        status.append(snap['discovery_status'])
    connection.send_result(msg['id'], {'racks': racks, 'total': len(racks),
        'online': sum(r['online'] and r['fresh'] for r in racks),
        'source_ips': sorted(set(sources)), 'discovery_status': '; '.join(status), 'read_only': True})


def async_register(hass):
    key = f'{DOMAIN}_cem3_ws_registered'
    if not hass.data.get(key):
        websocket_api.async_register_command(hass, websocket_cem3)
        hass.data[key] = True
