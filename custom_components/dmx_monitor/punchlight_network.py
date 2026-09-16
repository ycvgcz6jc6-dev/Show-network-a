"""Passive PunchLight DLi-LAN network discovery.

PunchLight documents DLi-LAN as an Apple MIDI / RTP-MIDI network endpoint.
This module only discovers advertised RTP-MIDI services; it never opens a
control session and never sends MIDI/control data to a discovered device.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)
APPLE_MIDI_SERVICE = "_apple-midi._udp.local."


def _is_punchlight_hint(value: str) -> bool:
    value = value.lower()
    return "punchlight" in value or "dli-lan" in value or value.startswith("dli")


def _scan_sync(zc, interface: str | None, timeout: float) -> list[dict[str, Any]]:
    try:
        from zeroconf import ServiceBrowser, ServiceListener
    except ImportError:
        return []

    found: dict[str, dict[str, Any]] = {}

    class Listener(ServiceListener):
        def add_service(self, zc, service_type, name):
            self._update(zc, service_type, name)

        def update_service(self, zc, service_type, name):
            self._update(zc, service_type, name)

        def remove_service(self, zc, service_type, name):
            found.pop(name, None)

        def _update(self, zc, service_type, name):
            try:
                info = zc.get_service_info(service_type, name, timeout=1200)
                if not info:
                    return
                addresses = []
                for addr in info.addresses_by_version(4):
                    try:
                        addresses.append(".".join(str(b) for b in addr))
                    except Exception:
                        continue
                server = str(info.server or "").rstrip(".")
                label = str(name).removesuffix(service_type).rstrip(".")
                haystack = f"{label} {server}"
                found[name] = {
                    "name": label or name,
                    "service": name,
                    "host": server or None,
                    "addresses": addresses,
                    "port": int(info.port or 0),
                    "type": "punchlight_dli_lan" if _is_punchlight_hint(haystack) else "rtpmidi_candidate",
                    "confidence": "high" if _is_punchlight_hint(haystack) else "candidate",
                    "evidence": ["mDNS/Bonjour _apple-midi._udp.local."],
                }
            except Exception as exc:
                _LOGGER.debug("PunchLight mDNS service parse failed for %s: %s", name, exc)

    browser = None
    try:
        # Home Assistant owns this shared Zeroconf instance. It already listens
        # on the network adapters enabled in HA. The optional interface value is
        # retained as scan metadata/API compatibility, but we must not create a
        # second Zeroconf socket just to bind one interface.
        listener = Listener()
        browser = ServiceBrowser(zc, APPLE_MIDI_SERVICE, listener)
        import time
        deadline = time.monotonic() + max(0.5, min(timeout, 10.0))
        while time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        # Cancel only our browser. Never close Home Assistant's shared Zeroconf.
        if browser is not None:
            try:
                browser.cancel()
            except Exception:
                pass
    return sorted(found.values(), key=lambda row: (row["type"] != "punchlight_dli_lan", row["name"].lower()))


async def async_scan(hass, interface: str | None = None, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Discover RTP-MIDI/Apple MIDI endpoints without sending control data."""
    from homeassistant.components import zeroconf as ha_zeroconf

    zc = await ha_zeroconf.async_get_instance(hass)
    return await asyncio.to_thread(_scan_sync, zc, interface, timeout)
