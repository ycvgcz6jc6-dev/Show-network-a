"""Read-only Nexus Audio gateway status monitor via its own management
API (project: github.com/ycvgcz6jc6-dev/Nexus-audio, "Nexus Audio by
Mct." -- an audio-input Home Assistant OS add-on bridging AirPlay,
Spotify Connect, native Dante RX and AES67 into Music Assistant as
Sendspin sources; conceptually the input-side counterpart to
spin2dante's own output-side Music-Assistant-to-Dante bridge).

Verified directly against the add-on's own source code (app/main.py's
do_GET/do_POST routing), not the README/DOCS.md alone -- the exact
routes below are read from the real implementation:
  GET  /health                 -- status, version, validation errors, system metrics
  GET  /api/interfaces         -- network interfaces
  GET  /api/sources            -- per-source worker/audio/PTP/Sendspin status
  GET  /api/dante               -- Dante-specific summary
  GET  /api/aes67/discovery      -- SAP/SDP discovered sessions
  POST /api/reload, /api/source/{save,delete,start,stop,restart},
       /api/aes67/select        -- control actions, NEVER called here

DELIBERATELY MONITORING-ONLY, matching this project's standing "read
first, control behind Active Control" rule applied identically to
QLab/Resolume/Millumin elsewhere in this codebase: only the five GET
routes above are ever requested. Starting, stopping, restarting a
source, reloading config, or selecting an AES67 session are all
POST-only in the real API and are never sent by this module.

The add-on's own documentation is explicit that its management port
(default 8099) has no authentication of its own and is meant for a
trusted local network only -- this module assumes the same trust
boundary Show Network already operates in (it never crosses a network
segment on its own), and never disables or bypasses anything on the
gateway's side.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

NEXUS_AUDIO_DEFAULT_PORT = 8099
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


@dataclass
class NexusAudioSourceStatus:
    id: str
    name: str | None = None
    type: str | None = None
    state: str | None = None
    process_alive: bool = False
    uptime_s: float | None = None
    restarts: int = 0
    audio_present: bool = False
    peak_dbfs: float | None = None
    error: str | None = None


@dataclass
class NexusAudioRecord:
    host: str
    online: bool = False
    version: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    sources: list[NexusAudioSourceStatus] = field(default_factory=list)
    last_poll: float | None = None
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "host": self.host, "online": self.online, "version": self.version,
            "validation_errors": self.validation_errors,
            "source_count": len(self.sources),
            "sources": [
                {"id": s.id, "name": s.name, "type": s.type, "state": s.state,
                 "process_alive": s.process_alive, "uptime_s": s.uptime_s,
                 "restarts": s.restarts, "audio_present": s.audio_present,
                 "peak_dbfs": s.peak_dbfs, "error": s.error}
                for s in self.sources
            ],
            "last_poll": self.last_poll, "error": self.error,
            "protocol": "Nexus Audio management API (verified against source)",
            "scope": "status_only_no_source_control",
        }


class NexusAudioMonitor:
    """Polls status for a set of configured Nexus Audio gateway hosts.
    Read-only: only ever sends GET /health and GET /api/sources.
    """

    def __init__(self, hosts: list[str], *, port: int = NEXUS_AUDIO_DEFAULT_PORT, timeout_s: float = 2.0):
        self.hosts = list(hosts)
        self.port = port
        self.timeout_s = timeout_s
        self.records: dict[str, NexusAudioRecord] = {}

    def _get_json(self, host: str, path: str) -> dict:
        url = f"http://{host}:{self.port}{path}"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=self.timeout_s) as response:  # nosec B310 - admin-configured local endpoint, GET only
            data = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(data) > _MAX_RESPONSE_BYTES:
            raise ValueError("Nexus Audio response too large")
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Nexus Audio payload must be an object")
        return payload

    async def _poll_one(self, host: str) -> NexusAudioRecord:
        record = NexusAudioRecord(host=host, last_poll=time.time())
        try:
            health = await asyncio.to_thread(self._get_json, host, "/health")
        except Exception as err:  # noqa: BLE001 - urllib/json can raise many distinct types; all mean "not reachable/usable"
            record.online = False
            record.error = f"{type(err).__name__}: {err}"
            return record

        record.online = True
        record.version = health.get("version")
        errs = health.get("validation_errors")
        record.validation_errors = list(errs) if isinstance(errs, list) else []

        try:
            sources_payload = await asyncio.to_thread(self._get_json, host, "/api/sources")
        except Exception:
            sources_payload = {}
        for row in sources_payload.get("sources") or []:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            audio = row.get("audio") if isinstance(row.get("audio"), dict) else {}
            record.sources.append(NexusAudioSourceStatus(
                id=str(row["id"]), name=row.get("name"), type=row.get("type"),
                state=row.get("state"), process_alive=bool(row.get("process_alive")),
                uptime_s=row.get("uptime_s"), restarts=row.get("restarts") or 0,
                audio_present=bool(audio.get("present")), peak_dbfs=audio.get("peak_dbfs"),
                error=row.get("error"),
            ))
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
