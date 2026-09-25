"""Rich device identity and network inventory.

IPs are connection metadata, never stable identity.  Identity prefers a trusted
serial number or MAC.  Each fact may carry an evidence source and confidence
so the UI can explain why a device/model/protocol was identified.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from time import time
import json
from pathlib import Path

@dataclass
class Evidence:
    field: str
    value: str
    source: str
    confidence: float = 1.0

@dataclass
class DeviceRecord:
    unique_id: str
    ip: str | None = None
    ipv6: str | None = None
    hostname: str | None = None
    mac: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    product_type: str | None = None
    serial: str | None = None
    firmware: str | None = None
    category: str | None = None
    vlan: int | None = None
    switch_name: str | None = None
    switch_port: str | None = None
    link_speed_mbps: int | None = None
    interface: str | None = None
    protocols: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: str = "unknown"
    confidence_score: float = 0.0
    first_seen: float = field(default_factory=time)
    last_seen: float = field(default_factory=time)
    custom_name: str | None = None
    custom_manufacturer: str | None = None
    custom_model: str | None = None
    custom_location: str | None = None
    custom_role: str | None = None
    hidden: bool = False
    monitor_mode: str = "auto"  # auto | monitor | ignore

    def display_name(self):
        return self.custom_name or self.hostname or self.model or self.manufacturer or self.unique_id

    def display_manufacturer(self):
        return self.custom_manufacturer or self.manufacturer

    def display_model(self):
        return self.custom_model or self.model

    def update_connection(self, ip=None, hostname=None, ipv6=None):
        if ip: self.ip = ip
        if hostname: self.hostname = hostname
        if ipv6: self.ipv6 = ipv6
        self.last_seen = time()

    def add_evidence(self, field: str, value, source: str, confidence: float = 1.0):
        if value is None:
            return
        self.evidence.append(Evidence(field, str(value), source, max(0.0, min(1.0, confidence))))
        self.confidence_score = max(self.confidence_score, confidence)

    def as_public_dict(self):
        data = asdict(self)
        data["display_name"] = self.display_name()
        data["display_manufacturer"] = self.display_manufacturer()
        data["display_model"] = self.display_model()
        data["protocols"] = sorted(self.protocols)
        data["sources"] = sorted(self.sources)
        data["evidence"] = [asdict(e) for e in self.evidence[-50:]]
        return data

class DeviceInventory:
    def __init__(self, storage_path: str | None = None):
        self.devices: dict[str, DeviceRecord] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        self.overrides: dict[str, dict] = {}
        self.load_overrides()

    def load_overrides(self):
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text())
            self.overrides = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            self.overrides = {}

    def save_overrides(self):
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.overrides, indent=2, ensure_ascii=False))
        tmp.replace(self.storage_path)

    def set_override(self, unique_id: str, **values):
        allowed = {"name": "custom_name", "manufacturer": "custom_manufacturer",
                   "model": "custom_model", "location": "custom_location",
                   "role": "custom_role", "hidden": "hidden", "monitor_mode": "monitor_mode"}
        if "monitor_mode" in values and values.get("monitor_mode") not in (None, "auto", "monitor", "ignore"):
            raise ValueError("monitor_mode must be auto, monitor or ignore")
        current = self.overrides.setdefault(unique_id, {})
        for key, value in values.items():
            if key in allowed and value is not None:
                current[allowed[key]] = value
        self._apply_override(unique_id)
        self.save_overrides()

    def clear_override(self, unique_id: str):
        self.overrides.pop(unique_id, None)
        self._apply_override(unique_id)
        self.save_overrides()

    def _apply_override(self, unique_id: str):
        device = self.devices.get(unique_id)
        override = self.overrides.get(unique_id, {})
        if not device:
            return
        for key in ("custom_name", "custom_manufacturer", "custom_model", "custom_location", "custom_role", "hidden", "monitor_mode"):
            if key in override:
                setattr(device, key, override[key])

    def apply_overrides(self):
        for uid in self.devices:
            self._apply_override(uid)

    def identity(self, *, serial=None, mac=None, fallback=None):
        if serial:
            return f"serial:{serial.lower()}"
        if mac:
            return f"mac:{mac.lower().replace(':','').replace('-','')}"
        return fallback or "unknown"

    def upsert(self, **kwargs):
        uid = self.identity(serial=kwargs.get("serial"), mac=kwargs.get("mac"), fallback=kwargs.get("unique_id"))
        device = self.devices.get(uid)
        # Discovery often sees an IP first (ARP/HTTP) and learns the stable MAC
        # later. Promote the existing candidate instead of creating a duplicate.
        #
        # This used to only run when serial/mac was present. That left a real
        # gap (audit-confirmed "duplicate IPs between ARP and DNS-SD"): ARP's
        # own fallback ids are interface-qualified ("candidate:<ip>:<iface>",
        # runtime/setup.py), but discovery_pipeline.mdns_result()'s fallback
        # is plain "candidate:<ip>" with no serial/mac -- so an mDNS hit for
        # an IP ARP had already recorded could never take this promotion
        # path and always created a second, separate record for the same
        # address. find_by_ip() already does the right thing with no
        # interface hint (only merges when exactly one existing record
        # matches that IP, declining on genuine ambiguity), so the fix is to
        # try promotion for any upsert carrying an IP, not just ones that
        # also carry a serial/mac.
        if device is None and kwargs.get("ip"):
            existing = self.find_by_ip(kwargs.get("ip"), interface=kwargs.get("interface"))
            if existing is not None and existing.unique_id != uid:
                old_uid = existing.unique_id
                self.devices.pop(old_uid, None)
                existing.unique_id = uid
                self.devices[uid] = existing
                if old_uid in self.overrides and uid not in self.overrides:
                    self.overrides[uid] = self.overrides.pop(old_uid)
                device = existing
        if device is None:
            device = DeviceRecord(unique_id=uid)
            self.devices[uid] = device
        for key in (
            "ip", "ipv6", "hostname", "mac", "manufacturer", "model", "product_type",
            "serial", "firmware", "category", "vlan", "switch_name", "switch_port", "link_speed_mbps", "interface",
        ):
            value = kwargs.get(key)
            if value is not None:
                setattr(device, key, value)
        device.protocols.update(kwargs.get("protocols", set()))
        device.sources.update(kwargs.get("sources", set()))
        for item in kwargs.get("evidence", []):
            if isinstance(item, Evidence):
                device.evidence.append(item)
            elif isinstance(item, dict):
                device.add_evidence(item.get("field", "unknown"), item.get("value"), item.get("source", "unknown"), float(item.get("confidence", 1.0)))
        if kwargs.get("confidence"):
            device.confidence = kwargs["confidence"]
        if kwargs.get("confidence_score") is not None:
            device.confidence_score = float(kwargs["confidence_score"])
        device.last_seen = time()
        self._apply_override(uid)
        return device

    def observe_physical_path(self, unique_id: str, *, switch_name: str, switch_port: str | None, link_speed_mbps=None, source: str = "LLDP-MIB", confidence: float = .98):
        """Attach a physical path only to an already identified device.

        This does not create or merge identities. It is intended for explicit
        evidence such as an exact unique LLDP hostname match. VLAN is not
        accepted here because LLDP remote-system/port evidence alone does not
        prove an endpoint VLAN/PVID.
        """
        device = self.devices.get(unique_id)
        if device is None:
            return None
        device.switch_name = switch_name
        device.switch_port = switch_port
        device.link_speed_mbps = link_speed_mbps
        device.add_evidence("switch_port", switch_port, source, confidence)
        return device

    def find_by_ip(self, ip, interface: str | None = None):
        """Find an address without crossing explicit interface boundaries.

        Show networks frequently reuse RFC1918 ranges on isolated NICs/VLANs.
        When the caller knows the receiving interface, an address observed on a
        different explicit interface is *not* the same identity.  An unscoped
        record (typically mDNS before ARP enrichment) may still be promoted when
        it is the only unscoped candidate.
        """
        matches = [d for d in self.devices.values() if d.ip == ip or d.ipv6 == ip]
        if interface is not None:
            exact = [d for d in matches if d.interface == interface]
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                return None
            unscoped = [d for d in matches if d.interface is None]
            return unscoped[0] if len(unscoped) == 1 else None
        return matches[0] if len(matches) == 1 else None

    def find_by_hostname_exact(self, hostname: str | None):
        """Return a unique device only for an explicit hostname equality.

        Custom/display/model/manufacturer labels are deliberately excluded: they
        are operator/UI metadata and are not sufficient evidence to merge LLDP
        identity.
        """
        key = str(hostname or "").strip().rstrip(".").casefold()
        if not key:
            return None
        matches = [d for d in self.devices.values()
                   if str(d.hostname or "").strip().rstrip(".").casefold() == key]
        return matches[0] if len(matches) == 1 else None

    def public(self, include_hidden=True):
        rows = [d.as_public_dict() for d in self.devices.values() if include_hidden or not d.hidden]
        return rows

    def summary(self):
        return {
            "total": len(self.devices),
            "confirmed": sum(d.confidence == "confirmed" for d in self.devices.values()),
            "candidates": sum(d.confidence == "candidate" for d in self.devices.values()),
            "unknown": sum(d.confidence == "unknown" for d in self.devices.values()),
        }
