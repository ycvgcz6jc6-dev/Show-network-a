"""Pure security helpers for the generic device web proxy.

Kept free of Home Assistant imports so the SSRF policy can be unit-tested in
plain CI. Operator-entered addresses are useful monitoring targets, but are not
by themselves proof that a remote HTTP target was observed on the show network.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urljoin, urlsplit

_OPERATOR_ONLY_SOURCES = {"operator", "manual", "operator_manual_target"}


def is_safe_ip_literal(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (addr.is_loopback or addr.is_multicast or addr.is_unspecified)


def device_is_network_observed(device) -> bool:
    """Require evidence beyond a manual/operator-only inventory insertion."""
    sources = {str(x).strip().lower() for x in (getattr(device, "sources", None) or set()) if str(x).strip()}
    if any(src not in _OPERATOR_ONLY_SOURCES for src in sources):
        return True
    evidence = getattr(device, "evidence", None) or []
    for item in evidence:
        source = getattr(item, "source", None)
        if source is None and isinstance(item, dict):
            source = item.get("source")
        src = str(source or "").strip().lower()
        if src and src not in _OPERATOR_ONLY_SOURCES:
            return True
    return False


def is_proxy_eligible_device_ip(coordinator, ip: str) -> bool:
    if not is_safe_ip_literal(ip):
        return False
    inventory = getattr(coordinator, "inventory", None)
    if inventory is None:
        return False
    matches = [d for d in inventory.devices.values() if getattr(d, "ip", None) == ip or getattr(d, "ipv6", None) == ip]
    # Ambiguous duplicate IPs (possible across multiple NICs) must not silently
    # select an arbitrary device. At least one network-observed record is needed.
    observed = [d for d in matches if device_is_network_observed(d)]
    return len(observed) >= 1


def validate_port(value, default: int) -> int:
    port = int(value if value not in (None, "") else default)
    if not 1 <= port <= 65535:
        raise ValueError("port out of range")
    return port


def validated_redirect(current_url: str, location: str, allowed_ip: str) -> str | None:
    """Resolve a redirect only when it remains HTTP(S) on the exact target IP."""
    if not location:
        return None
    candidate = urljoin(current_url, location)
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    host = parsed.hostname
    if not host:
        return None
    try:
        if ipaddress.ip_address(host) != ipaddress.ip_address(allowed_ip):
            return None
    except ValueError:
        # Hostnames are intentionally rejected: DNS rebinding must not expand
        # an IP-literal inventory authorization into arbitrary name resolution.
        return None
    try:
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
    except ValueError:
        return None
    return candidate
