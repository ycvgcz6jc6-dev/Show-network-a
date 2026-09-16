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

HTTP_MARKERS=(
    ("Luminex", ("luminex", "gigacore"), "HTTP"),
    ("MA Lighting", ("grandma3", "grand ma3", "ma lighting"), "Web Remote"),
    ("Aruba", ("aruba networks", "arubaos", "procurve"), "HTTP"),
    ("Cisco", ("cisco", "catalyst"), "HTTP"),
    ("NETGEAR", ("netgear",), "HTTP"),
    ("Ubiquiti", ("ubiquiti", "unifi", "edgeswitch"), "HTTP"),
    ("MikroTik", ("mikrotik", "routeros"), "HTTP"),
    ("TP-Link", ("tp-link", "tplink", "jetstream", "omada"), "HTTP"),
    ("L-Acoustics", ("l-acoustics", "l acoustics", "la network manager"), "Audio device HTTP"),
    ("d&b audiotechnik", ("d&b audiotechnik", "dbaudio", "db audiotechnik"), "Audio device HTTP"),
    ("Powersoft", ("powersoft",), "Audio device HTTP"),
    ("Lab Gruppen/Lake", ("lab gruppen", "lake processing", "lake controller"), "Audio device HTTP"),
    ("QSC", ("q-sys", "qsc"), "Audio device HTTP"),
    ("Yamaha", ("yamaha pro audio",), "Audio device HTTP"),
)

def fingerprint_http(headers=None, body=""):
    headers={str(k).lower():str(v) for k,v in (headers or {}).items()}
    text=(body or "").lower(); server=headers.get("server","").lower(); title=headers.get("x-powered-by","").lower()
    hay=f"{server} {title} {text}"
    for vendor,markers,protocol in HTTP_MARKERS:
        marker=next((m for m in markers if m in hay),None)
        if marker:
            return FingerprintResult(vendor,None,protocol,"confirmed",(f"{vendor} marker observed in HTTP response: {marker}",))
    return FingerprintResult(None,None,"HTTP","candidate",())

MDNS_MARKERS=(
    ("Audinate", ("_netaudio-", "dante", "audinate"), "Dante"),
    ("Luminex", ("luminex", "gigacore"), "mDNS"),
    ("L-Acoustics", ("l-acoustics", "l acoustics", "la network"), "Audio network"),
    ("d&b audiotechnik", ("d&b", "dbaudio", "db audiotechnik"), "Audio network"),
    ("Powersoft", ("powersoft",), "Audio network"),
    ("Lab Gruppen/Lake", ("lab gruppen", "lake"), "Audio network"),
    ("QSC", ("qsc", "q-sys"), "Audio network"),
    ("Yamaha", ("yamaha",), "Audio network"),
)

def fingerprint_mdns(service_type="",name="",properties=None):
    props={str(k).lower():str(v).lower() for k,v in (properties or {}).items()}
    hay=" ".join([str(service_type).lower(),str(name).lower(),*props.keys(),*props.values()])
    for vendor,markers,protocol in MDNS_MARKERS:
        marker=next((m for m in markers if m in hay),None)
        if marker:
            return FingerprintResult(vendor,None,protocol,"confirmed",(f"{vendor} marker observed in Zeroconf data: {marker}",))
    return FingerprintResult(None,None,None,"unknown",())

def fingerprint_protocol_observation(protocol, evidence):
    if not protocol:return FingerprintResult(None,None,None,"unknown",())
    return FingerprintResult(None,None,protocol,"candidate",tuple(evidence or ()))

# Public IEEE allocation hints used only as manufacturer evidence. The longer
# Luminex IAB prefix must be checked before the MA-L/OUI prefix.
MAC_PREFIXES=(
    ("Luminex", "0050c29c9"),
    ("Luminex", "d0699e"),
)

def fingerprint_mac(mac: str | None):
    compact=''.join(c for c in str(mac or '').lower() if c in '0123456789abcdef')
    for vendor,prefix in MAC_PREFIXES:
        if compact.startswith(prefix):
            return FingerprintResult(vendor,None,'MAC/OUI','confirmed',(f'{vendor} registered MAC prefix {prefix}',))
    return FingerprintResult(None,None,None,'unknown',())
