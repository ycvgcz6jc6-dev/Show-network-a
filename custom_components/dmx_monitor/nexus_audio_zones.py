"""Lightweight, spin2dante-style read-only Nexus Audio status via the
Music Assistant media_player entities Nexus Audio itself creates for
each of its sources.

WHY THIS EXISTS ALONGSIDE nexus_audio_monitor.py (the direct HTTP
management-API client): that module polls Nexus Audio's own real,
documented management API (GET /health, GET /api/sources) directly --
a legitimate but heavier mechanism, matching the Resolume/QLab pattern
used elsewhere. On request, this module offers the lighter alternative
instead: no network calls of its own at all, just reading entity state
Home Assistant already keeps current -- the exact same "read another
integration's own entities" pattern already used for spin2dante
(sendspin_dante_zones.py).

Nexus Audio's own documentation states it "converts those inputs to
PCM and exposes them as Sendspin Live Inputs to Music Assistant" --
each configured source (AirPlay, Spotify Connect, Dante RX, AES67)
therefore registers its own Music Assistant media_player entity,
mirroring spin2dante's own sources-as-players design on the output
side.

CANDIDATE STATUS, NOT YET LIVE-VERIFIED (same honesty standard as
sendspin_dante_zones.py's own dante_subscriber_status field): unlike
spin2dante, this specific entity shape has not been confirmed against
a real running Nexus Audio installation's actual Home Assistant state.
`state`/`volume_level`/`is_volume_muted` are read the same way as any
other media_player (a stable, documented Home Assistant entity
contract, not a Nexus-Audio-specific guess) -- those parts are safe
regardless. What is NOT yet confirmed live is which entity_ids
correspond to which Nexus Audio source; the user must currently supply
them explicitly, the same requirement already in place for spin2dante's
own zones.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NexusAudioZoneStatus:
    entity_id: str
    name: str
    found: bool
    state: str | None = None
    active: bool = False
    volume_level: float | None = None
    muted: bool | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id, "name": self.name, "found": self.found,
            "state": self.state, "active": self.active,
            "volume_level": self.volume_level, "muted": self.muted,
        }


class NexusAudioZoneMonitor:
    """Reads the state of user-designated media_player entities (the
    Music Assistant players Nexus Audio registers for its configured
    sources) from the live hass state machine. No polling, no sockets,
    no HTTP request of any kind -- hass.states is already kept current
    by Home Assistant's own event bus. Identical mechanism to
    SendspinDanteZoneMonitor for spin2dante.
    """

    def __init__(self, hass, entity_ids: list[str]):
        self.hass = hass
        self.entity_ids = list(entity_ids)

    def snapshot(self) -> list[dict[str, Any]]:
        rows = []
        for entity_id in self.entity_ids:
            state_obj = self.hass.states.get(entity_id)
            if state_obj is None:
                rows.append(NexusAudioZoneStatus(entity_id=entity_id, name=entity_id, found=False).snapshot())
                continue
            attrs = state_obj.attributes or {}
            rows.append(NexusAudioZoneStatus(
                entity_id=entity_id,
                name=attrs.get("friendly_name") or entity_id,
                found=True,
                state=state_obj.state,
                active=state_obj.state == "playing",
                volume_level=attrs.get("volume_level"),
                muted=attrs.get("is_volume_muted"),
            ).snapshot())
        return rows
