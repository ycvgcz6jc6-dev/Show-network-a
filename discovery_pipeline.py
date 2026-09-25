"""Discovery -> fingerprint -> inventory pipeline."""
from __future__ import annotations
from .device_inventory import DeviceInventory
from .device_fingerprints import fingerprint_http, fingerprint_mdns, fingerprint_protocol_observation

class DiscoveryPipeline:
    def __init__(self, inventory=None):
        self.inventory=inventory or DeviceInventory()

    def http_result(self, ip, headers=None, body=""):
        fp=fingerprint_http(headers,body)
        return self.inventory.upsert(
            ip=ip, manufacturer=fp.vendor, model=fp.model,
            protocols={fp.protocol} if fp.protocol else set(),
            sources={"http_fingerprint"}, confidence=fp.confidence,
            unique_id=f"candidate:{ip}"
        )

    def mdns_result(self, ip, service_type="", name="", properties=None):
        if not ip and not name:
            # Audit-confirmed: "une ligne vide affichée comme si elle
            # existait" on the Network page. Without an IP or a name, the
            # only thing left to key an inventory record on is the bare
            # service_type ("mdns:_http._tcp.local." style) -- not
            # device-specific, so every mDNS announcement of that service
            # type from *any* device on the network collapses into one
            # shared, near-empty phantom record that keeps getting
            # touched and never represents one real piece of equipment.
            # There is nothing useful to attribute this evidence to yet;
            # skip creating an inventory row for it rather than fabricate
            # one that just displays as blank.
            return None
        fp=fingerprint_mdns(service_type,name,properties)
        protocol = fp.protocol or (f"mDNS:{service_type.rstrip('.')}" if service_type else "mDNS")
        fallback = f"candidate:{ip}" if ip else f"mdns:{name or service_type}"
        return self.inventory.upsert(
            ip=ip or None, hostname=name or None, manufacturer=fp.vendor,
            model=fp.model, protocols={protocol},
            sources={"zeroconf"}, confidence=fp.confidence if fp.confidence != "unknown" else "candidate",
            confidence_score=0.9 if fp.confidence == "confirmed" else 0.55,
            evidence=[{"field":"service_type","value":service_type,"source":"zeroconf","confidence":0.8}],
            unique_id=fallback
        )

    def protocol_result(self, ip, protocol, evidence=None, mac=None, serial=None):
        fp=fingerprint_protocol_observation(protocol,evidence)
        return self.inventory.upsert(
            ip=ip, mac=mac, serial=serial,
            protocols={protocol}, sources={"passive_protocol"},
            confidence=fp.confidence, unique_id=f"candidate:{ip}"
        )
