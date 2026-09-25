"""Read-only Yamaha DM3/DM7/Rivage PM scene status monitor via the
officially documented YOSC protocol.

Verified directly against Yamaha's own published OSC Specifications
(DM7 Series OSC Specifications Version 1.1.0,
https://data.yamaha.com/files/download/other_assets/5/2234295/DM7_osc_specs_V110_en.pdf)
-- not inferred, not reverse-engineered, matching this project's
standing rule to only use documented protocol elements.

DELIBERATELY NARROW IN SCOPE. The official spec documents /set (control
of fader levels, mutes, names, etc.) extensively, and one genuine
read/query action for scene status -- sscurrentt_ex ("Scene Get Current
Scene_A/B Number", <type tag> s: string) -- but does NOT document a
generic get for arbitrary MIXER:Current/... channel parameters (fader
level, mute state, and so on). A community-built, hardware-confirmed
Chataigne module for the DM7 reports that a generic Get/Subscribe
exists as an undocumented "escape hatch" on the real console, and that
push/subscribe doesn't reliably work for per-channel values anyway
(poll-only in practice) -- but without that generic get's exact syntax
appearing in Yamaha's own published specification, guessing at it here
would break the same "never use an undocumented protocol element" rule
this project applies everywhere else (SNMP MIBs verified against RFC
text, LLDP-EXT-DOT1-MIB verified against the raw MIB source, etc.). So:
scene status only, built entirely from the one query action Yamaha
itself documents.

CL/QL/TF consoles are NOT covered by this module -- they only speak the
older RCP protocol (TCP 49280), for which Yamaha publishes no
documentation of its own at all (unofficial community reverse-
engineering only). DiGiCo and Soundcraft are not covered by any module
in this project for their own, different reasons (see doctor.py/
aes70_monitor.py neighbours and project chat history: DiGiCo's Generic
OSC is operator-configured per installation, not a fixed external API;
Soundcraft Ui is community-reverse-engineered and Vi/Si has no external
protocol at all).
"""
from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass

from .osc_output import encode_osc
from .osc_receiver import parse_basic_message

YOSC_PORT = 49900  # "IP Port No.: UDP 49900" -- OSC Specifications 1.3


@dataclass
class YamahaOSCRecord:
    host: str
    name: str | None = None
    online: bool = False
    scene_a_current: str | None = None
    scene_b_current: str | None = None
    last_poll: float | None = None
    error: str | None = None

    def snapshot(self) -> dict:
        return {
            "host": self.host, "name": self.name or self.host, "online": self.online,
            "scene_a_current": self.scene_a_current, "scene_b_current": self.scene_b_current,
            "last_poll": self.last_poll, "error": self.error,
            "protocol": "Yamaha YOSC (official DM3/DM7/Rivage PM OSC spec)",
            "scope": "scene_status_only",
        }


class YamahaOSCMonitor:
    """Polls current-scene status for a set of configured Yamaha DM3/
    DM7/Rivage PM consoles. Read-only: the only OSC action this module
    ever sends is the officially documented sscurrentt_ex query -- never
    /set, /event, or any control action.
    """

    def __init__(self, hosts: dict[str, str | None], *, timeout_s: float = 1.5):
        self.hosts = dict(hosts)
        self.timeout_s = timeout_s
        self.records: dict[str, YamahaOSCRecord] = {}

    async def _query_scene(self, host: str, scene_list: str) -> str | None:
        """scene_list is 'scene_a' or 'scene_b'. Sends
        /yosc:req/sscurrentt_ex <scene_list> and parses the string reply
        -- exactly the address/argument shape documented in the official
        spec's Snapshot table (Action=sscurrentt_ex becomes the address
        suffix, Parameter ID=scene_a/scene_b is the sole argument, no
        value since this is a query not a set)."""
        loop = asyncio.get_running_loop()
        packet = encode_osc("/yosc:req/sscurrentt_ex", [scene_list])
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        try:
            await loop.sock_sendto(sock, packet, (host, YOSC_PORT))
            data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=self.timeout_s)
            _address, values = parse_basic_message(data)
            return str(values[0]) if values else None
        finally:
            sock.close()

    async def _poll_one(self, host: str, name: str | None) -> YamahaOSCRecord:
        record = YamahaOSCRecord(host=host, name=name, last_poll=time.time())
        try:
            record.scene_a_current = await self._query_scene(host, "scene_a")
            record.scene_b_current = await self._query_scene(host, "scene_b")
            record.online = True
        except (OSError, asyncio.TimeoutError, ValueError) as err:
            record.online = False
            record.error = f"{type(err).__name__}: {err}"
        return record

    async def async_update(self) -> None:
        if not self.hosts:
            return
        results = await asyncio.gather(
            *(self._poll_one(host, name) for host, name in self.hosts.items()),
            return_exceptions=True,
        )
        for host, result in zip(self.hosts, results):
            if isinstance(result, Exception):
                continue
            self.records[host] = result

    def snapshot(self) -> list[dict]:
        return [rec.snapshot() for rec in self.records.values()]
