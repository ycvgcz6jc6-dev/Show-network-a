"""Passive ELC dmXLAN device inventory and protocol capability model.

No proprietary ELC commands are sent by this module. It only normalizes
observations supplied by the discovery pipeline and known ELC capabilities.
"""
from dataclasses import dataclass, field
from typing import Any

KNOWN_MODELS = {
    # Catalog metadata only; capabilities are applied only when an explicit
    # model string is observed by the discovery pipeline. Sources: ELC
    # product pages (dmXLAN Node 1S/3/GBx 8/HD 24/Buddy).
    "dmXLAN Node 1S": {
        "dmx_ports": 1,
        "poe": True,
        "bidirectional_dmx": True,
        "rdm": False,
        "protocols": ["sACN", "Art-Net", "Shownet"],
    },
    "dmXLAN Node 3": {
        "dmx_ports": 3,
        "ethernet": "100M",
        "bidirectional_dmx": True,
        "rdm": True,
        "protocols": ["sACN", "Art-Net", "Shownet", "RTTrPL"],
    },
    "dmXLAN NodeGBx 8": {
        "dmx_ports": 8,
        "ethernet": "Gigabit",
        "ethernet_ports": 2,
        "bidirectional_dmx": True,
        "rdm": True,
        "protocols": ["sACN", "Art-Net", "Shownet", "RTTrPL"],
    },
    "dmXLAN NodeHD 24": {
        "dmx_ports": 24,
        "ethernet": "Gigabit",
        "ethernet_ports": 2,
        "bidirectional_dmx": True,
        "rdm": True,
        "protocols": ["sACN", "Art-Net", "Shownet", "RTTrPL"],
    },
    "dmXLAN Buddy": {
        "dmx_ports": 2,
        "ethernet": "USB-B + Ethernet",
        "bidirectional_dmx": True,
        "rdm": "output_only",
        "protocols": ["sACN", "Art-Net", "Shownet"],
    },
}

@dataclass
class ELCObservation:
    address: str
    model: str | None = None
    source: str = "unknown"
    protocols: set[str] = field(default_factory=set)
    last_seen: float | None = None
    evidence: list[str] = field(default_factory=list)

    @property
    def capabilities(self) -> dict[str, Any]:
        caps = dict(KNOWN_MODELS.get(self.model or "", {}))
        caps.setdefault("protocols", sorted(self.protocols))
        return caps

class ELCInventory:
    """Conservative ELC inventory; identity is never guessed from an IP alone."""
    def __init__(self) -> None:
        self.devices: dict[str, ELCObservation] = {}

    def observe(self, address: str, *, model: str | None = None, source: str = "network", protocols=None, evidence=None, last_seen=None) -> ELCObservation:
        obs = self.devices.get(address) or ELCObservation(address=address)
        if model:
            obs.model = model
        obs.source = source
        obs.protocols.update(protocols or [])
        obs.evidence.extend(evidence or [])
        if last_seen is not None:
            obs.last_seen = last_seen
        self.devices[address] = obs
        return obs

    def snapshot(self) -> list[dict[str, Any]]:
        return [{"address": d.address, "model": d.model, "source": d.source, "protocols": sorted(d.protocols), "last_seen": d.last_seen, "evidence": d.evidence[-10:], "capabilities": d.capabilities} for d in self.devices.values()]
