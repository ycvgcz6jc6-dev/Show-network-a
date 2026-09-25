"""Show Network notification service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "set_notification_config"):
        async def _set_notification_config(call):
            c = coordinator_for_call(hass, call)
            c.notifications.enabled = bool(call.data.get("enabled", False))
            c.notifications.target = str(call.data.get("target", "persistent")).strip()
            c.notifications.mode = str(call.data.get("mode", "both"))
            c.data["notification"] = {"enabled": c.notifications.enabled, "target": c.notifications.target, "mode": c.notifications.mode}
            c.publish(notification=c.data["notification"])
            if c.archive:
                c.archive.record("ha", "notification_config_changed", {"enabled": c.notifications.enabled, "configured": bool(c.notifications.target)})
        hass.services.async_register(DOMAIN, "set_notification_config", guarded(_set_notification_config))
