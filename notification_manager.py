"""Native Home Assistant notification bridge for Show Network."""
from __future__ import annotations
import logging
from typing import Any
_LOGGER = logging.getLogger(__name__)

class ShowNetworkNotifications:
    def __init__(self, hass, target: str | None = None, enabled: bool = False, mode: str = "both") -> None:
        self.hass = hass
        self.target = (target or "").strip()
        self.enabled = bool(enabled)
        self.mode = mode if mode in {"notify", "persistent", "both"} else "both"
        self._last_key = None

    async def async_notify(self, title: str, message: str, severity: str = "warning", dedupe_key: str | None = None) -> bool:
        if not self.enabled:
            return False
        key = dedupe_key or f"{severity}:{title}:{message}"
        if key == self._last_key and severity != "critical":
            return False
        self._last_key = key
        sent = False
        try:
            if self.mode in {"persistent", "both"} or self.target == "persistent":
                await self.hass.services.async_call("persistent_notification", "create", {
                    "title": f"Show Network — {title}",
                    "message": message,
                    "notification_id": f"show_network_{key.replace(':', '_')[:100]}",
                }, blocking=False)
                sent = True
            if self.mode in {"notify", "both"} and self.target and self.target != "persistent":
                service = self.target.removeprefix("notify.")
                if not service or not self.hass.services.has_service("notify", service):
                    _LOGGER.warning("Show Network notification service not found: notify.%s", service)
                else:
                    await self.hass.services.async_call("notify", service, {
                        "title": f"Show Network — {title}",
                        "message": message,
                        "data": {"tag": "show_network", "severity": severity},
                    }, blocking=False)
                    sent = True
            return sent
        except Exception as err:
            _LOGGER.warning("Show Network notification failed: %s", err)
            return sent
