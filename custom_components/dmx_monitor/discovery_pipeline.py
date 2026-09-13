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
        fp=fingerprint_mdns(service_type,name,properties)
        return self.inventory.upsert(
            ip=ip, hostname=name or None, manufacturer=fp.vendor,
            model=fp.model, protocols={fp.protocol} if fp.protocol else set(),
            sources={"zeroconf_fingerprint"}, confidence=fp.confidence,
            unique_id=f"candidate:{ip}"
        )

    def protocol_result(self, ip, protocol, evidence=None, mac=None, serial=None):
        fp=fingerprint_protocol_observation(protocol,evidence)
        return self.inventory.upsert(
            ip=ip, mac=mac, serial=serial,
            protocols={protocol}, sources={"passive_protocol"},
            confidence=fp.confidence, unique_id=f"candidate:{ip}"
        )
