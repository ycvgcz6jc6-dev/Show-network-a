"""Read-only QLab status monitor via Figure 53's officially published OSC
Dictionary.

Verified directly against QLab's own documentation
(https://qlab.app/docs/v5/scripting/osc-dictionary-v5/) -- not inferred,
not reverse-engineered. Unlike DiGiCo's Generic OSC (operator-configured
per installation, no fixed external API) or Soundcraft's Ui protocol
(community reverse-engineered, the vendor's own word was "this isn't
supported"), QLab's OSC API is Figure 53's first-party, documented
control surface.

DELIBERATELY MONITORING-ONLY, matching the rapport maître's own stated
priority for this phase ("Monitoring/read-only d'abord... GO/Panic/etc.
protégés"). Only ever sends three read-only queries, all explicitly
documented as accepted even without a passcode:
  - /version           -- QLab's version number
  - /workspaces         -- open workspaces (name, unique ID, port)
  - /workspace/{id}/thump -- heartbeat/connection check ("thump-thump")
Never sends /go, /panic, /stop, or any cue/workspace control message.

Reply format (documented): QLab replies to a query with
/reply/{the/address/queried} followed by a single string argument
containing JSON -- e.g. querying /version gets back a reply whose
address is /reply/version and whose one argument is the JSON string
"5.6.1". This module decodes that reply shape specifically, not a
general QLab message parser.
"""
from __future__ import annotations

import asyncio
import json
import socket
import time
from dataclasses import dataclass, field

from .osc_output import encode_osc
from .osc_receiver import parse_basic_message

QLAB_DEFAULT_PORT = 53000  # "QLab listens for incoming OSC on port 53000."


@dataclass
class QLabWorkspace:
    unique_id: str
    display_name: str | None = None
    port: int | None = None
    version: str | None = None
    thump_ok: bool = False


@dataclass
class QLabRecord:
    host: str
    online: bool = False
    version: str | None = None
    workspaces: list[QLabWorkspace] = field(default_factory=list)
    last_poll: float | None = None
    error: str | None = None

    def snapshot(self) -> dict:
        return {
            "host": self.host, "online": self.online, "version": self.version,
            "workspace_count": len(self.workspaces),
            "workspaces": [
                {"unique_id": w.unique_id, "display_name": w.display_name,
                 "port": w.port, "version": w.version, "thump_ok": w.thump_ok}
                for w in self.workspaces
            ],
            "last_poll": self.last_poll, "error": self.error,
            "protocol": "QLab OSC (official Figure 53 dictionary)",
            "scope": "status_only_no_cue_control",
        }


async def _query(host: str, port: int, address: str, timeout: float) -> object | None:
    """Send one read-only OSC query over UDP and parse its JSON reply.
    Returns None if no reply arrives or the reply can't be parsed as the
    documented /reply/{address} {json_string} shape."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        packet = encode_osc(address, [])
        await loop.sock_sendto(sock, packet, (host, port))
        data = await asyncio.wait_for(loop.sock_recv(sock, 8192), timeout=timeout)
        reply_address, values = parse_basic_message(data)
        if not values:
            return None
        try:
            return json.loads(values[0])
        except (ValueError, TypeError):
            return values[0]
    except (OSError, asyncio.TimeoutError):
        return None
    finally:
        sock.close()


class QLabMonitor:
    """Polls status for a set of configured QLab hosts. Read-only: only
    ever sends /version, /workspaces, and per-workspace /thump.
    """

    def __init__(self, hosts: list[str], *, port: int = QLAB_DEFAULT_PORT, timeout_s: float = 1.5):
        self.hosts = list(hosts)
        self.port = port
        self.timeout_s = timeout_s
        self.records: dict[str, QLabRecord] = {}

    async def _poll_one(self, host: str) -> QLabRecord:
        record = QLabRecord(host=host, last_poll=time.time())
        version = await _query(host, self.port, "/version", self.timeout_s)
        if version is None:
            record.online = False
            record.error = "no reply to /version"
            return record
        record.online = True
        record.version = str(version) if not isinstance(version, (dict, list)) else None

        workspaces_raw = await _query(host, self.port, "/workspaces", self.timeout_s)
        if isinstance(workspaces_raw, list):
            for w in workspaces_raw:
                if not isinstance(w, dict):
                    continue
                ws = QLabWorkspace(
                    unique_id=str(w.get("uniqueID", "")),
                    display_name=w.get("displayName"),
                    port=w.get("port"),
                    version=w.get("version"),
                )
                thump = await _query(host, self.port, f"/workspace/{ws.unique_id}/thump", self.timeout_s)
                ws.thump_ok = thump == "thump"
                record.workspaces.append(ws)
        return record

    async def async_update(self) -> None:
        if not self.hosts:
            return
        results = await asyncio.gather(*(self._poll_one(h) for h in self.hosts), return_exceptions=True)
        for host, result in zip(self.hosts, results):
            if isinstance(result, Exception):
                continue
            self.records[host] = result

    def snapshot(self) -> list[dict]:
        return [rec.snapshot() for rec in self.records.values()]
