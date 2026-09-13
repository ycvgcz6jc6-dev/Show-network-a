"""Conservative protocol/device fingerprinting.

A fingerprint may raise confidence only from evidence actually observed.
No device is identified from an IP address alone.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FingerprintResult:
    vendor: str | None
    model: str | None
    protocol: str | None
    confidence: str
    evidence: tuple[str,...]

def fingerprint_http(headers=None, body=""):
    headers={str(k).lower():str(v) for k,v in (headers or {}).items()}
    text=(body or "").lower()
    server=headers.get("server","").lower()
    evidence=[]
    if "luminex" in server or "luminex" in text:
        evidence.append("Luminex marker observed in HTTP response")
        return FingerprintResult("Luminex",None,"GigaCore/API","confirmed",tuple(evidence))
    if "grandma3" in text or "grand ma3" in text:
        evidence.append("grandMA3 marker observed in HTTP response")
        return FingerprintResult("MA Lighting",None,"Web Remote","confirmed",tuple(evidence))
    return FingerprintResult(None,None,None,"candidate",())

def fingerprint_mdns(service_type="",name="",properties=None):
    s=f"{service_type} {name}".lower()
    props={str(k).lower():str(v).lower() for k,v in (properties or {}).items()}
    evidence=[]
    if "dante" in s or "dante" in str(props):
        evidence.append("Dante marker observed in Zeroconf data")
        return FingerprintResult("Audinate",None,"Dante","confirmed",tuple(evidence))
    return FingerprintResult(None,None,None,"unknown",())

def fingerprint_protocol_observation(protocol, evidence):
    """Protocol presence alone identifies a protocol, not necessarily a vendor/model."""
    if not protocol:
        return FingerprintResult(None,None,None,"unknown",())
    return FingerprintResult(None,None,protocol,"candidate",tuple(evidence or ()))
