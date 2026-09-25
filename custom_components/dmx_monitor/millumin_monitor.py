"""Passive Millumin status monitor via its documented OSC feedback
messages.

Verified against Millumin's official OSC documentation (Millumin V5,
github.com/anome/millumin-dev-kit/wiki/OSC-documentation,
help.millumin.com/docs/connect/osc-api/) -- not inferred.

WHY PASSIVE LISTENING IS THE CORE MECHANISM (/ping IS A ONE-SHOT NUDGE,
NOT THE MAIN PATH):
Millumin's separate "feedback" mechanism (opt-in, enabled via "API
feedback" in Millumin's own Device Manager) is precisely documented:
every feedback message is prefixed /millumin and has an exact,
published address+argument shape --
  /millumin/board/launchedColumn [index, "name"]
  /millumin/board/stoppedColumn [index, "name"]
  /millumin/layer:{name}/mediaStarted [index, "name", duration]
  /millumin/layer:{name}/mediaPaused [index, "name"]
  /millumin/layer:{name}/mediaStopped [index, "name"]
  (and the same forms addressed by /millumin/index:{n}/... instead)
Building on the precisely-documented mechanism rather than an ambiguous
one matches this project's standing rule to never guess at an
unconfirmed wire format -- and it's architecturally consistent with
every other passive observer in this codebase (audio_ptp.py, dante.py,
greengo_monitor.py): listen for what the device already announces,
never poll it for the core status stream.

/ping (github.com/anome/millumin-dev-kit and Millumin's own forum,
confirmed directly by Millumin's developer: "the '/ping' OSC message is
meant to be used by other applications, in order to get all
information about Millumin's current project") is a genuine, official,
read-only query -- but Millumin's own developer also confirmed on that
same forum thread that /ping "only has effect if the API/feedback is
toggled on", i.e. it can only ever produce the *same* feedback messages
already documented above, not a separate, differently-shaped reply.
Given that, sending it once at startup is a safe, well-evidenced way to
get an initial snapshot immediately rather than waiting for the first
real state change, routed through the exact same message handler as
everything else -- it changes nothing about what this module can
interpret, only how soon the first update arrives. Never sent
repeatedly, never relied on as the primary mechanism.

REQUIRES ONE-TIME SETUP IN MILLUMIN ITSELF: the user must add Show
Network as an OSC device in Millumin's own Device Manager (Cmd+K -> OSC
tab) with "API feedback" checked, pointing it at whichever host/port
this monitor is configured to listen on -- the same "both ends must
agree on an address" pairing this project already asks for with
Green-GO's multicast group (greengo_monitor.py).
"""
from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass, field

from .osc_receiver import OSCReceiver
from .osc_output import encode_osc

_ELEMENT_ADDRESS_RE = re.compile(r"^(?:layer|index):.+$")


@dataclass
class MilluminLayerStatus:
    identifier: str
    media_name: str | None = None
    playing: bool = False
    duration: float | None = None
    last_event: str | None = None
    last_seen: float | None = None


class MilluminMonitor:
    """Passively listens for Millumin's documented OSC feedback
    messages. Never sends anything -- not even the /ping this module
    deliberately avoids relying on (see module docstring).
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 7000,
                 ping_target: tuple[str, int] | None = None):
        self.host = host
        self.port = port
        self.ping_target = ping_target
        self.receiver = OSCReceiver(host=host, port=port, callback=self._on_message)
        self.layers: dict[str, MilluminLayerStatus] = {}
        self.current_column: dict | None = None
        self.messages_received = 0
        self.last_message_at: float | None = None
        self.ping_sent = False

    async def start(self) -> None:
        await self.receiver.start()
        if self.ping_target:
            self._send_ping()

    def _send_ping(self) -> None:
        """One-shot, fire-and-forget /ping at startup -- see module
        docstring for why this is safe (a documented, read-only query
        that Millumin's own developer confirmed only ever produces the
        same feedback shape already handled by _on_message) and why it
        is never repeated (this is a nudge for a faster first snapshot,
        not the module's primary mechanism)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto(encode_osc("/millumin/ping", []), self.ping_target)
            finally:
                sock.close()
            self.ping_sent = True
        except OSError:
            pass  # a failed nudge just means the first update arrives on its own

    async def stop(self) -> None:
        await self.receiver.stop()

    def _on_message(self, message) -> None:
        address = getattr(message, "address", "")
        if not address.startswith("/millumin/"):
            return  # only documented feedback messages are ever interpreted
        values = getattr(message, "values", ()) or ()
        self.messages_received += 1
        self.last_message_at = time.time()
        parts = address[len("/millumin/"):].split("/")
        if not parts or not parts[0]:
            return

        if parts[0] == "board" and len(parts) >= 2:
            action = parts[1]
            if action in ("launchedColumn", "stoppedColumn"):
                self.current_column = {
                    "index": values[0] if values else None,
                    "name": values[1] if len(values) > 1 else None,
                    "state": "launched" if action == "launchedColumn" else "stopped",
                    "at": self.last_message_at,
                }
            return

        if not _ELEMENT_ADDRESS_RE.match(parts[0]):
            return  # not a layer:/index: addressed message this module tracks
        element_id = parts[0]
        action = parts[-1] if len(parts) > 1 else None
        layer = self.layers.setdefault(element_id, MilluminLayerStatus(identifier=element_id))
        layer.last_seen = self.last_message_at
        if action == "mediaStarted":
            layer.playing = True
            layer.last_event = "started"
            layer.media_name = values[1] if len(values) > 1 else None
            layer.duration = values[2] if len(values) > 2 else None
        elif action == "mediaPaused":
            layer.playing = False
            layer.last_event = "paused"
        elif action == "mediaStopped":
            layer.playing = False
            layer.last_event = "stopped"
            layer.media_name = None

    def snapshot(self) -> dict:
        return {
            "listening_on": f"{self.host}:{self.port}",
            "ping_target": f"{self.ping_target[0]}:{self.ping_target[1]}" if self.ping_target else None,
            "ping_sent": self.ping_sent,
            "messages_received": self.messages_received,
            "last_message_at": self.last_message_at,
            "feedback_active": self.messages_received > 0,
            "current_column": self.current_column,
            "layers": [
                {"identifier": l.identifier, "playing": l.playing, "media_name": l.media_name,
                 "duration": l.duration, "last_event": l.last_event, "last_seen": l.last_seen}
                for l in self.layers.values()
            ],
            "protocol": "Millumin OSC feedback (official, documented addresses only)",
            "scope": "passive_feedback_only_nothing_ever_sent",
        }
