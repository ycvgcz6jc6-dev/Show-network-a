"""Canonical protocol adapter catalogue and capability metadata."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .adapters import (
    AES67Monitor, AvbPassiveInspector, DanteMonitor, DmxNetworkReceiver,
    EnttecDmxInput, MANet3Listener, MIDIInputRuntime, OSCReceiver,
    PTPMonitor, PunchLightState, ST2110PassiveInspector,
)

@dataclass(frozen=True, slots=True)
class AdapterSpec:
    key: str
    category: str
    constructor: Callable[..., Any]
    receive_only: bool = True
    blocking_policy: str = "async_or_worker"

ADAPTERS = {
    "dmx-network": AdapterSpec("dmx-network", "LIGHT", DmxNetworkReceiver),
    "enttec": AdapterSpec("enttec", "LIGHT", EnttecDmxInput),
    "ma-net3": AdapterSpec("ma-net3", "LIGHT", MANet3Listener),
    "osc": AdapterSpec("osc", "CONTROL", OSCReceiver),
    "midi": AdapterSpec("midi", "CONTROL", MIDIInputRuntime),
    "dante": AdapterSpec("dante", "AUDIO", DanteMonitor),
    "aes67": AdapterSpec("aes67", "AUDIO", AES67Monitor),
    "ptp": AdapterSpec("ptp", "AUDIO", PTPMonitor),
    "st2110": AdapterSpec("st2110", "VIDEO", ST2110PassiveInspector),
    "avb": AdapterSpec("avb", "AUDIO", AvbPassiveInspector),
    "punchlight": AdapterSpec("punchlight", "CONTROL", PunchLightState),
}

def get_adapter_spec(key: str) -> AdapterSpec:
    try:
        return ADAPTERS[key]
    except KeyError as exc:
        raise ValueError(f"Unknown Show Network adapter: {key}") from exc
