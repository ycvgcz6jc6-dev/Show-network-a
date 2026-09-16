"""KORG controller profiles for the CONTROL / MIDI layer.

The nanoKONTROL2 is a USB-MIDI control surface. We keep it receive-only from
Home Assistant: MIDI messages coming from the hardware are observed and fed
into the unified Mapping Engine. No MIDI OUT is sent to the controller.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class KorgControllerProfile:
    model: str
    manufacturer: str = "KORG"
    protocol: str = "MIDI"
    direction: str = "input"


NANOKONTROL2 = KorgControllerProfile("nanoKONTROL2")


def identify_korg_controller(port_name: str | None) -> KorgControllerProfile | None:
    """Identify a supported KORG USB-MIDI controller from its port name."""
    if not port_name:
        return None
    name = port_name.lower()
    if "nanokontrol2" in name or "nano kontrol2" in name:
        return NANOKONTROL2
    return None
