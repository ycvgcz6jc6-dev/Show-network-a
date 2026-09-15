"""Conservative passive Dante endpoint inventory from observed mDNS/DNS-SD.

The parser intentionally stays read-only and only exposes identity evidence that was
actually present in DNS-SD packets.  It does not attempt Dante routing/control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import struct
import time

DANTE_SERVICE_MARKERS = (
    "_netaudio-arc._udp.local",
    "_netaudio-dbc._udp.local",
    "_netaudio-cmc._udp.local",
    "_netaudio-chan._udp.local",
    "_netaudio-dante._udp.local",
    "_dante._udp.local",
)


def _read_name(data: bytes, offset: int, *, max_jumps: int = 16) -> tuple[str, int]:
    """Decode a DNS name, including compression pointers, with bounds guards."""
    labels: list[str] = []
    pos = offset
    consumed = 0
    jumped = False
    jumps = 0
    seen: set[int] = set()
    while True:
        if pos >= len(data):
            raise ValueError("dns name outside packet")
        length = data[pos]
        if length == 0:
            if not jumped:
                consumed += 1
            break
        if length & 0xC0 == 0xC0:
            if pos + 1 >= len(data):
                raise ValueError("truncated dns pointer")
            pointer = ((length & 0x3F) << 8) | data[pos + 1]
            if pointer >= len(data) or pointer in seen or jumps >= max_jumps:
                raise ValueError("invalid dns pointer")
            seen.add(pointer)
            jumps += 1
            if not jumped:
                consumed += 2
            pos = pointer
            jumped = True
            continue
        if length & 0xC0:
            raise ValueError("unsupported dns label type")
        pos += 1
        if pos + length > len(data):
            raise ValueError("truncated dns label")
        label = data[pos:pos + length].decode("utf-8", "replace")
        labels.append(label)
        if not jumped:
            consumed += 1 + length
        pos += length
    return ".".join(labels), offset + consumed


def _parse_txt(raw: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    pos = 0
    while pos < len(raw):
        ln = raw[pos]
        pos += 1
        if pos + ln > len(raw):
            break
        item = raw[pos:pos + ln].decode("utf-8", "replace")
        pos += ln
        key, sep, value = item.partition("=")
        if key:
            out[key] = value if sep else ""
    return out


@dataclass
class DanteEndpoint:
    source: str
    first_seen: float
    last_seen: float
    packets: int = 0
    services: set[str] = field(default_factory=set)
    instances: set[str] = field(default_factory=set)
    hostnames: set[str] = field(default_factory=set)
    addresses: set[str] = field(default_factory=set)
    txt: dict[str, str] = field(default_factory=dict)
    evidence: set[str] = field(default_factory=set)


class DanteInventory:
    def __init__(self) -> None:
        self.endpoints: dict[str, DanteEndpoint] = {}
        self.parse_errors = 0

    @staticmethod
    def _records(payload: bytes) -> list[dict]:
        if len(payload) < 12:
            raise ValueError("short dns packet")
        qd, an, ns, ar = struct.unpack_from("!HHHH", payload, 4)
        pos = 12
        for _ in range(qd):
            _, pos = _read_name(payload, pos)
            if pos + 4 > len(payload):
                raise ValueError("truncated dns question")
            pos += 4
        rows: list[dict] = []
        for _ in range(an + ns + ar):
            name, pos = _read_name(payload, pos)
            if pos + 10 > len(payload):
                raise ValueError("truncated dns rr")
            rtype, rclass, ttl, rdlen = struct.unpack_from("!HHIH", payload, pos)
            pos += 10
            end = pos + rdlen
            if end > len(payload):
                raise ValueError("truncated dns rdata")
            rows.append({"name": name, "type": rtype, "class": rclass, "ttl": ttl, "rdata_offset": pos, "rdata": payload[pos:end]})
            pos = end
        return rows

    def observe(self, source: str, payload: bytes) -> None:
        now = time.time()
        try:
            records = self._records(payload)
        except (ValueError, struct.error):
            self.parse_errors += 1
            return

        item = self.endpoints.get(source)
        if item is None:
            item = DanteEndpoint(source, now, now)
            self.endpoints[source] = item
        item.last_seen = now
        item.packets += 1
        item.addresses.add(source)

        for rr in records:
            name = rr["name"].rstrip(".")
            lname = name.lower()
            rtype = rr["type"]
            try:
                if rtype == 12:  # PTR
                    target, _ = _read_name(payload, rr["rdata_offset"])
                    target = target.rstrip(".")
                    if any(marker in lname for marker in DANTE_SERVICE_MARKERS) or "netaudio" in lname or "dante" in lname:
                        item.services.add(name)
                        item.instances.add(target)
                        item.evidence.add(f"PTR:{name}->{target}")
                elif rtype == 33 and ("netaudio" in lname or "dante" in lname or any(inst.lower() == lname for inst in item.instances)):
                    raw = rr["rdata"]
                    if len(raw) >= 6:
                        port = struct.unpack_from("!H", raw, 4)[0]
                        target, _ = _read_name(payload, rr["rdata_offset"] + 6)
                        item.hostnames.add(target.rstrip("."))
                        item.instances.add(name)
                        item.evidence.add(f"SRV:{name}:{port}->{target.rstrip('.')}")
                elif rtype == 16 and ("netaudio" in lname or "dante" in lname or any(inst.lower() == lname for inst in item.instances)):
                    item.txt.update(_parse_txt(rr["rdata"]))
                    item.instances.add(name)
                    item.evidence.add(f"TXT:{name}")
                elif rtype == 1 and len(rr["rdata"]) == 4:
                    addr = str(ipaddress.IPv4Address(rr["rdata"]))
                    # Correlate an A record when it is the sender address or a host already tied to a Dante service.
                    if addr == source or name in item.hostnames:
                        item.addresses.add(addr)
                        item.hostnames.add(name)
                        item.evidence.add(f"A:{name}->{addr}")
            except (ValueError, struct.error, ipaddress.AddressValueError):
                self.parse_errors += 1

    def snapshot(self) -> dict:
        now = time.time()
        rows = []
        for e in sorted(self.endpoints.values(), key=lambda x: x.source):
            if not e.services and not e.instances and not e.hostnames:
                continue
            age = max(0.0, now - e.last_seen)
            rows.append({
                "source": e.source,
                "packets": e.packets,
                "services": sorted(e.services),
                "instances": sorted(e.instances),
                "hostnames": sorted(e.hostnames),
                "addresses": sorted(e.addresses),
                "txt": dict(sorted(e.txt.items())),
                "identity_evidence": sorted(e.evidence)[:50],
                "display_name": (sorted(e.instances)[0] if e.instances else (sorted(e.hostnames)[0] if e.hostnames else None)),
                "last_seen": e.last_seen,
                "age_s": round(age, 3),
                "fresh": age < 20.0,
                "identity_confidence": "dns_sd_observed",
            })
        return {
            "dante_endpoints": len(rows),
            "dante_fresh_endpoints": sum(1 for r in rows if r["fresh"]),
            "dante_inventory": rows,
            "dante_dns_parse_errors": self.parse_errors,
            "dante_inventory_note": "Passive DNS-SD identity evidence only; no Dante routing/control API is used.",
        }
