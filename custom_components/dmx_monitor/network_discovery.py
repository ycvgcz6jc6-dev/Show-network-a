"""Passive local neighbor discovery helpers.

No packets are emitted. The Linux ARP cache is read when available and merged
with mDNS/protocol observations by the runtime discovery pipeline.
"""
from __future__ import annotations
from pathlib import Path

def arp_neighbors(path: str = "/proc/net/arp") -> list[dict]:
    p = Path(path)
    try:
        lines = p.read_text().splitlines()
    except OSError:
        return []
    rows = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        ip, _hw_type, flags, mac, _mask, device = parts[:6]
        if mac == "00:00:00:00:00:00":
            continue
        try:
            complete = bool(int(flags, 16) & 0x2)
        except ValueError:
            complete = False
        rows.append({"ip": ip, "mac": mac.lower(), "interface": device, "complete": complete, "source": "arp_cache"})
    return rows
