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
    "elc": ("dmxlan", "dmxlan", "elc lighting"),
}


def _scan_sync(timeout: float = 2.0) -> list[dict[str, Any]]:
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        return []
    found: dict[str, dict[str, Any]] = {}
    browsers = []
    zc = Zeroconf()

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
                if not vendor:
                    return
                found[(service_type, name)] = {
                    "vendor": vendor,
                    "name": str(name).rstrip("."),
                    "service_type": service_type,
                    "host": str(info.server or "").rstrip(".") or None,
                    "addresses": addresses,
                    "port": int(info.port or 0),
                    "evidence": [f"mDNS marker observed: {vendor}"],
                    "observed_at": time.time(),
                }
            except Exception:
                return

    listener = Listener()
    try:
        # Standard DNS-SD meta service: discover advertised service types first.
        class TypeListener(ServiceListener):
            def add_service(self, zc_, service_type, name):
                if name.endswith("._tcp.local.") or name.endswith("._udp.local."):
                    browsers.append(ServiceBrowser(zc_, name, listener))
            def update_service(self, zc_, service_type, name): pass
            def remove_service(self, zc_, service_type, name): pass
        ServiceBrowser(zc, "_services._dns-sd._udp.local.", TypeListener())
        deadline = time.monotonic() + max(0.5, min(timeout, 5.0))
        while time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        try:
            zc.close()
        except Exception:
            pass
    return list(found.values())


async def async_scan(timeout: float = 2.0) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_scan_sync, timeout)
