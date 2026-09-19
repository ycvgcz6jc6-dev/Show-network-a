"""Passive Green-GO Communication inventory and health model.

This module deliberately avoids proprietary Green-GO control/configuration.
It normalizes observations from the generic discovery/network layers and known
public product capabilities. No Green-GO commands are sent.
"""
from dataclasses import dataclass, field
from typing import Any

KNOWN_MODELS = {
    # Names/capabilities are metadata only. They are applied only when the
    # discovery layer supplies an explicit model string; an IP/mDNS vendor
    # marker alone never guesses a model.
    "GGO-BPX": {"category": "wired_beltpack", "channels": 32},
    "GGO-WBPX": {"category": "wireless_beltpack", "channels": 32},
    "MCXD": {"category": "multichannel_station"},
    "MCXD-EXT": {"category": "multichannel_extension"},
}

@dataclass
class GreenGOObservation:
    address: str
    model: str | None = None
    source: str = "unknown"
    last_seen: float | None = None
    evidence: list[str] = field(default_factory=list)

    @property
    def capabilities(self) -> dict[str, Any]:
        return dict(KNOWN_MODELS.get(self.model or "", {}))

class GreenGOInventory:
    """Conservative Green-GO inventory; IP alone never becomes device identity."""
    def __init__(self) -> None:
        self.devices: dict[str, GreenGOObservation] = {}

    def observe(self, address: str, *, model: str | None = None, source: str = "network", evidence=None, last_seen=None) -> GreenGOObservation:
        obs = self.devices.get(address) or GreenGOObservation(address=address)
        if model:
            obs.model = model
        obs.source = source
        obs.evidence.extend(evidence or [])
        if last_seen is not None:
            obs.last_seen = last_seen
        self.devices[address] = obs
        return obs

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"address": d.address, "model": d.model, "source": d.source,
             "last_seen": d.last_seen, "evidence": d.evidence[-10:],
             "capabilities": d.capabilities}
            for d in self.devices.values()
        ]
