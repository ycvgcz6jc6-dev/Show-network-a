"""Read-only spin2dante Dante-zone status via the Music Assistant
media_player entities spin2dante itself creates.

BACKGROUND (verified live against a real installation, not guessed):
spin2dante (github.com/salanki/spin2dante) is a Sendspin-to-Dante bridge
Home Assistant add-on with NO exposed web UI, ingress, or REST/WebSocket
API (confirmed via its Supervisor add-on record: ingress=false,
webui=null). It DOES emit rich, structured per-bridge status as add-on
container log lines (stream start/idle transitions, drift/sync figures,
volume changes) -- but reading those continuously would require calling
the Home Assistant Supervisor's add-on-logs API, which is only available
to actual Supervisor add-ons that declare `hassio_api: true` in their own
config.yaml and read the SUPERVISOR_TOKEN environment variable Supervisor
injects into their container. A regular custom_component (what Show
Network is) has neither of those and cannot obtain them -- this is a
real architectural boundary in Home Assistant, not a missing feature of
this integration, and reproducing it would break the moment this runs
under Docker/Core-only installs even where it happened to work under
HAOS.

What IS both real and safely usable: each spin2dante "bridge" (one
Sendspin-to-Dante audio path, configured in spin2dante's own add-on
options) registers itself as an ordinary Music Assistant `media_player`
entity, and that entity's `state` tracks spin2dante's own idle/streaming
transitions directly (confirmed live: a bridge's log line "stream ended,
entering idle" corresponds exactly to that entity's state becoming
"idle"; "bridge volume set to N" corresponds to volume_level updating to
N/100). Reading another integration's ordinary entity state is a normal,
always-available capability for any Home Assistant component -- no
Supervisor access, no undocumented protocol, no guessing.

This module does NOT attempt to distinguish "a real Dante receiver is
subscribed" from "Music Assistant is merely idle/playing" -- spin2dante
has a real, documented option for that distinction (`report_dante_subscriber`
per bridge: reports "Synchronized" only once an actual Dante receiver has
subscribed, "ExternalSource" otherwise), but it is off by default and
was not enabled on the monitored installation at the time this was
written. If enabled, its effect would need to be re-verified against a
live state read before this module's status interpretation is extended
to rely on it.

CANDIDATE FIELD (`dante_subscriber_status`, marked as such, never
asserted as fact): once `report_dante_subscriber` is enabled, spin2dante's
own documentation states it changes what gets "reported to Music
Assistant" as "Synchronized"/"ExternalSource" -- the only Music
Assistant player attribute observed carrying this kind of descriptive
text live on the monitored installation (before the option was enabled)
was `source` (seen as "Music Assistant Queue" there). This module reads
that same attribute and, only if its value happens to be exactly
"Synchronized" or "ExternalSource", surfaces it as a real Dante-side
subscription signal -- otherwise the field stays None, never guessed.
This has NOT been confirmed against a live read with the option
actually enabled; that confirmation is what would upgrade this from
"candidate" to verified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Exact strings from spin2dante's own documentation
# (github.com/salanki/spin2dante): what `report_dante_subscriber`
# changes the Music Assistant player's `source` attribute to report.
_DANTE_SUBSCRIBED_VALUE = "Synchronized"
_DANTE_NOT_SUBSCRIBED_VALUE = "ExternalSource"


@dataclass
class DanteZoneStatus:
    entity_id: str
    name: str
    found: bool
    state: str | None = None
    active: bool = False
    volume_level: float | None = None
    muted: bool | None = None
    dante_subscriber_status: str | None = None  # candidate, see module docstring

    def snapshot(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id, "name": self.name, "found": self.found,
            "state": self.state, "active": self.active,
            "volume_level": self.volume_level, "muted": self.muted,
            "dante_subscriber_status": self.dante_subscriber_status,
            "dante_subscriber_status_verified": False,  # flip to True once confirmed live
        }


class SendspinDanteZoneMonitor:
    """Reads the state of user-designated media_player entities (the
    Music Assistant players spin2dante registers for its configured
    bridges) from the live hass state machine. No polling, no sockets,
    no external process -- hass.states is already kept current by Home
    Assistant's own event bus.
    """

    def __init__(self, hass, entity_ids: list[str]):
        self.hass = hass
        self.entity_ids = list(entity_ids)

    def snapshot(self) -> list[dict[str, Any]]:
        rows = []
        for entity_id in self.entity_ids:
            state_obj = self.hass.states.get(entity_id)
            if state_obj is None:
                rows.append(DanteZoneStatus(entity_id=entity_id, name=entity_id, found=False).snapshot())
                continue
            attrs = state_obj.attributes or {}
            source_value = attrs.get("source")
            dante_status = source_value if source_value in (_DANTE_SUBSCRIBED_VALUE, _DANTE_NOT_SUBSCRIBED_VALUE) else None
            rows.append(DanteZoneStatus(
                entity_id=entity_id,
                name=attrs.get("friendly_name") or entity_id,
                found=True,
                state=state_obj.state,
                active=state_obj.state == "playing",
                volume_level=attrs.get("volume_level"),
                muted=attrs.get("is_volume_muted"),
                dante_subscriber_status=dante_status,
            ).snapshot())
        return rows
