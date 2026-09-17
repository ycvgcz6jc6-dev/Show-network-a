"""AUDIOFOCUS A Series (SCiO) passive listener -- SCAFFOLD, NOT YET FUNCTIONAL.

STATUS: reserved place, protocol details pending a real packet capture.

What is confirmed (from AUDIOFOCUS's own "A Series Operation Manual",
v1.1, section "Notes on networking"):

    "The communication protocol used by the A Series is UDP/IP based. It
    is based on Unicast communications (point-to-point) for the remote
    control of properties (e.g., modifying an input gain or the frequency
    of a filter) and Multicast (point-to-multipoint) for auto-discovery of
    devices and property changes (such as driving meters within SCIO).
    Multicasting is preferred over broadcasting as it is more suited for
    network bandwidth control."

So: a proprietary UDP protocol, unicast for control (out of scope for this
project regardless -- receive-only), multicast for device auto-discovery
AND live metering/property-change updates. That second part is exactly the
kind of thing this project already listens to passively for other vendors
(Dante, MA-Net3, Art-Net ArtPollReply) -- genuinely worth doing here too.

What is NOT confirmed, and was not found in any public AUDIOFOCUS
documentation, developer resource, or third-party writeup:
    - the multicast group address(es) and port(s) used
    - the discovery/announcement packet format
    - the metering/property-change packet format
    - whether the format differs between SCiO firmware versions

Filling any of that in without evidence would be exactly the "invented
telemetry" this project's own philosophy rules out (see e.g.
video_ip_supervision.py's NDI handling, or artnet_discovery.py's reliance
on the *standard* ArtPoll/ArtPollReply spec rather than guesswork). The
concrete next step is a real capture: on the same network segment as a
live A Series amplifier, e.g.

    sudo tcpdump -i <interface> -w audiofocus_capture.pcap "net 224.0.0.0/4"

...while refreshing the SCiO WebUI (to catch a discovery announcement) and
letting some audio play (to catch a metering update). Once that capture is
available, _parse_discovery_packet() and _parse_metering_packet() below
are where the real parsing logic goes, following the exact same
test-driven pattern already used throughout this codebase (see
artnet_discovery.py, st2110.py, snmp.py for the precedent: hand-decode the
real bytes, write the parser, prove it against a real or faithfully
reconstructed packet before wiring it into runtime/setup.py).

Text-based identification of AUDIOFOCUS devices already works today
without any of this, via data/spectacle_profiles.yaml + data/
manufacturers.yaml (manufacturer_profiles.match_manufacturer()) -- if an
AUDIOFOCUS device's name ever surfaces in mDNS, SNMP sysDescr, or any other
already-supported passive evidence source, it is already identified by
manufacturer today. This module is specifically about the SCiO multicast
discovery/metering channel described above, which needs the real capture
to implement correctly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioFocusDevice:
    ip: str
    name: str | None = None
    model: str | None = None  # e.g. "A 1504 SCiO" -- from a discovery announcement, once decoded
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    # Metering/status fields intentionally left undefined until the real
    # packet format is known -- see module docstring. No placeholder
    # temperature/level/fault fields are added here on spec, since an
    # empty dataclass honestly signals "not implemented" whereas a
    # populated-looking one inviting the reader to assume it works.


class AudioFocusInventory:
    """Passive registry for AUDIOFOCUS A Series devices.

    NOT YET WIRED into runtime/setup.py: there is no multicast listener
    behind this yet (see module docstring for why). observe_discovery() /
    observe_metering() exist as the intended entry points once a real
    packet capture lets _parse_discovery_packet() / _parse_metering_packet()
    be written for real, but they currently do nothing (see NotImplementedError
    below) rather than silently accepting and mis-parsing arbitrary bytes.
    """

    def __init__(self) -> None:
        self.devices: dict[str, AudioFocusDevice] = {}

    @staticmethod
    def _parse_discovery_packet(data: bytes) -> dict[str, Any] | None:
        """TODO once a real capture is available. See module docstring."""
        raise NotImplementedError(
            "AUDIOFOCUS discovery packet format is not yet known -- "
            "see audiofocus.py's module docstring for how to capture one."
        )

    @staticmethod
    def _parse_metering_packet(data: bytes) -> dict[str, Any] | None:
        """TODO once a real capture is available. See module docstring."""
        raise NotImplementedError(
            "AUDIOFOCUS metering packet format is not yet known -- "
            "see audiofocus.py's module docstring for how to capture one."
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "audiofocus_devices": [],
            "audiofocus_device_count": 0,
            "audiofocus_note": (
                "Scaffold only: AUDIOFOCUS's SCiO multicast discovery/metering "
                "protocol is UDP-based but its exact packet format is not "
                "publicly documented. Awaiting a real packet capture before "
                "any parsing logic is implemented -- see audiofocus.py."
            ),
        }
