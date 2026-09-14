"""Conservative passive mDNS vendor observation.

This is not a vendor protocol implementation. It only records a candidate when
an advertised mDNS service name/host/property contains an explicit vendor
marker. No connection, query, control or write is performed against devices.
"""
from __future__ import annotations
import asyncio
import time
from typing import Any

MARKERS = {
    "green_go": ("green-go", "greengo"),
    "elc": ("dmxlan", "elc lighting"),
    "dante": ("_netaudio-", "dante", "audinate"),
    "luminex": ("luminex", "gigacore"),
}


def _scan_sync(zc, timeout: float = 2.0) -> list[dict[str, Any]]:
    try:
        from zeroconf import ServiceBrowser, ServiceListener
    except ImportError:
        return []
    found: dict[str, dict[str, Any]] = {}
    browsers = []

    class Listener(ServiceListener):
        def add_service(self, zc_, service_type, name): self._update(zc_, service_type, name)
        def update_service(self, zc_, service_type, name): self._update(zc_, service_type, name)
        def remove_service(self, zc_, service_type, name): found.pop((service_type, name), None)
        def _update(self, zc_, service_type, name):
            try:
                info = zc_.get_service_info(service_type, name, timeout=1000)
                if not info:
                    return
                addresses = [".".join(str(b) for b in a) for a in info.addresses_by_version(4)]
                props = {str(k, "utf-8", "ignore").lower(): str(v, "utf-8", "ignore").lower() if isinstance(v, bytes) else str(v).lower() for k, v in (info.properties or {}).items()}
                label = str(name).lower()
                haystack = " ".join([label, str(info.server or "").lower(), service_type.lower(), *props.keys(), *props.values()])
                vendor = next((v for v, markers in MARKERS.items() if any(m in haystack for m in markers)), None)
                found[(service_type, name)] = {
                    "vendor": vendor,
                    "name": str(name).rstrip("."),
                    "service_type": service_type,
                    "host": str(info.server or "").rstrip(".") or None,
                    "addresses": addresses,
                    "port": int(info.port or 0),
                    "properties": props,
                    "evidence": ([f"mDNS vendor marker observed: {vendor}"] if vendor else [f"mDNS service observed: {service_type}" ]),
                    "observed_at": time.time(),
                }
            except Exception:
                return

    listener = Listener()
    type_browser = None
    try:
        # Standard DNS-SD meta service: discover advertised service types first.
        class TypeListener(ServiceListener):
            def add_service(self, zc_, service_type, name):
                if name.endswith("._tcp.local.") or name.endswith("._udp.local."):
                    browsers.append(ServiceBrowser(zc_, name, listener))
            def update_service(self, zc_, service_type, name): pass
            def remove_service(self, zc_, service_type, name): pass
        type_browser = ServiceBrowser(zc, "_services._dns-sd._udp.local.", TypeListener())
        deadline = time.monotonic() + max(0.5, min(timeout, 5.0))
        while time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        # Cancel only the browsers created by this scan. The Zeroconf instance
        # itself is shared and owned by Home Assistant.
        for browser in browsers:
            try:
                browser.cancel()
            except Exception:
                pass
        if type_browser is not None:
            try:
                type_browser.cancel()
            except Exception:
                pass
    return list(found.values())


async def async_scan(hass, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Observe vendor mDNS records using Home Assistant's shared Zeroconf."""
    from homeassistant.components import zeroconf as ha_zeroconf

    zc = await ha_zeroconf.async_get_instance(hass)
    return await asyncio.to_thread(_scan_sync, zc, timeout)
