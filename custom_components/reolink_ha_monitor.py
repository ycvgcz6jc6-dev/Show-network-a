"""Read-only Reolink camera status via Home Assistant's own official,
built-in Reolink integration -- not a custom Reolink API client.

WHY THIS APPROACH (matching sendspin_dante_zones.py's identical reasoning
for spin2dante/Music Assistant): Home Assistant's core `reolink`
integration already talks to the camera/NVR over Reolink's own
(undocumented, proprietary) protocol and exposes the results as normal
entities. Reading those entities is a standard, always-available
capability for any component -- no new network client, no protocol to
verify, no risk of conflicting with the official integration's own
connection to the device.

Entity shape verified directly against Home Assistant's own
integration documentation (home-assistant.io/integrations/reolink/):
for each camera, detection-type binary sensors are named
binary_sensor.<camera name>_motion / _person / _vehicle / _pet /
_animal / _visitor (doorbell press) / _package -- exactly which ones
exist depends on what the specific camera model supports.

Cameras are found via the entity registry's own `platform` field
(== "reolink"), not by matching against entity_id text -- robust to
custom friendly names, unlike a naming-convention guess. Binary sensors
are then correlated to their camera by shared `device_id`, the same
device grouping Home Assistant itself already uses for entities that
belong to one physical camera.
"""
from __future__ import annotations

from typing import Any


class ReolinkHAMonitor:
    """Reads Reolink camera + detection-sensor entities that Home
    Assistant's own official `reolink` integration already created and
    maintains. No polling of its own, no sockets -- hass.states/
    entity_registry are already kept current by Home Assistant's own
    event bus and the reolink integration's own connection to the
    camera/NVR.
    """

    def __init__(self, hass):
        self.hass = hass

    def snapshot(self) -> dict[str, Any]:
        try:
            from homeassistant.helpers import entity_registry as er
        except ImportError:
            return {"available": False, "reason": "entity_registry helper unavailable", "cameras": []}

        registry = er.async_get(self.hass)
        camera_entries = [
            entry for entry in registry.entities.values()
            if entry.platform == "reolink" and entry.entity_id.startswith("camera.")
        ]
        if not camera_entries:
            return {"available": True, "cameras": [], "camera_count": 0}

        sensor_entries_by_device: dict[str, list] = {}
        for entry in registry.entities.values():
            if entry.platform == "reolink" and entry.entity_id.startswith("binary_sensor."):
                sensor_entries_by_device.setdefault(entry.device_id, []).append(entry)

        cameras = []
        for cam_entry in camera_entries:
            state_obj = self.hass.states.get(cam_entry.entity_id)
            detections = []
            for sensor_entry in sensor_entries_by_device.get(cam_entry.device_id, []):
                sensor_state = self.hass.states.get(sensor_entry.entity_id)
                # Detection type is the entity_id's own trailing segment
                # (e.g. "..._person" -> "person"), matching the exact
                # naming convention documented by Home Assistant itself.
                kind = sensor_entry.entity_id.rsplit("_", 1)[-1]
                detections.append({
                    "entity_id": sensor_entry.entity_id, "kind": kind,
                    "active": sensor_state.state == "on" if sensor_state else None,
                    "available": sensor_state is not None and sensor_state.state != "unavailable",
                })
            cameras.append({
                "entity_id": cam_entry.entity_id,
                "name": (state_obj.attributes.get("friendly_name") if state_obj else None) or cam_entry.entity_id,
                "state": state_obj.state if state_obj else None,
                "available": state_obj is not None and state_obj.state != "unavailable",
                "detections": detections,
            })

        return {"available": True, "camera_count": len(cameras), "cameras": cameras}
