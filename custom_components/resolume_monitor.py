"""Read-only Resolume Arena/Avenue status monitor via the officially
published REST API.

Verified directly against Resolume's own documentation
(resolume.com/docs/restapi/, an OpenAPI 3.0 specification -- even more
formally documented than QLab's OSC dictionary) and cross-checked
against Resolume's own support pages and several independent, mutually
corroborating third-party integrations (grandMA3 plugin, Bitfocus
Companion module, community forum threads):
  - The webserver defaults to port 8080 for Arena/Avenue.
  - GET /api/v1/composition returns the full current composition state
    (layers, clips, and their playback status) in one call -- explicitly
    confirmed by Resolume's own forum support: "you can GET /composition
    data, and the currently playing clip with that."
  - Resolume's own webserver adds permissive CORS headers and behaves as
    a normal JSON HTTP API.
  - Parameter values are wrapped objects, not raw JSON leaves: a field
    like a clip's "connected" status looks like
    {"id": ..., "valuetype": "ParamState", "value": "Connected", ...},
    not a bare string -- confirmed by a real captured payload reported
    on Resolume's own forum.

DELIBERATELY MONITORING-ONLY, matching the rapport maître's own stated
priority for this phase ("Monitoring/read-only d'abord... GO/Panic/etc.
protégés"). Only ever sends a GET to /api/v1/composition -- never a
POST/PUT to trigger a clip, column, or any other control action.

This project does not have a full, exhaustive field-by-field schema for
this API the way it does for QLab's fully-documented OSC dictionary or
the IETF-standard SNMP MIBs used elsewhere -- parsing here is
deliberately defensive (every field read with .get(), nothing assumed
present) rather than treating any field as guaranteed.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

RESOLUME_DEFAULT_PORT = 8080
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # composition payloads can be sizeable; bounded, not unlimited


def _param_value(raw: Any) -> Any:
    """Resolume wraps parameter values in an object
    ({"id":..., "valuetype":..., "value":...}); unwrap defensively,
    since this project has no exhaustive schema for every field shape
    this API can return."""
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


@dataclass
class ResolumeLayerStatus:
    name: str | None
    playing_clip_name: str | None = None
    active: bool = False


@dataclass
class ResolumeRecord:
    host: str
    online: bool = False
    layers: list[ResolumeLayerStatus] = field(default_factory=list)
    last_poll: float | None = None
    error: str | None = None

    def snapshot(self) -> dict:
        return {
            "host": self.host, "online": self.online,
            "layer_count": len(self.layers),
            "active_layer_count": sum(1 for l in self.layers if l.active),
            "layers": [
                {"name": l.name, "active": l.active, "playing_clip_name": l.playing_clip_name}
                for l in self.layers
            ],
            "last_poll": self.last_poll, "error": self.error,
            "protocol": "Resolume REST API (official OpenAPI spec)",
            "scope": "status_only_no_playback_control",
        }


class ResolumeMonitor:
    """Polls composition status for a set of configured Resolume hosts.
    Read-only: only ever sends GET /api/v1/composition.
    """

    def __init__(self, hosts: list[str], *, port: int = RESOLUME_DEFAULT_PORT, timeout_s: float = 2.0):
        self.hosts = list(hosts)
        self.port = port
        self.timeout_s = timeout_s
        self.records: dict[str, ResolumeRecord] = {}

    def _fetch(self, host: str) -> dict:
        url = f"http://{host}:{self.port}/api/v1/composition"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=self.timeout_s) as response:  # nosec B310 - admin-configured local endpoint, GET only
            data = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(data) > _MAX_RESPONSE_BYTES:
            raise ValueError("Resolume composition response too large")
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Resolume composition payload must be an object")
        return payload

    async def _poll_one(self, host: str) -> ResolumeRecord:
        record = ResolumeRecord(host=host, last_poll=time.time())
        try:
            payload = await asyncio.to_thread(self._fetch, host)
        except Exception as err:  # noqa: BLE001 - urllib/json can raise many distinct types; all mean "not reachable/usable"
            record.online = False
            record.error = f"{type(err).__name__}: {err}"
            return record

        record.online = True
        for layer_raw in payload.get("layers") or []:
            if not isinstance(layer_raw, dict):
                continue
            name = _param_value(layer_raw.get("name"))
            playing_name = None
            active = False
            for clip_raw in layer_raw.get("clips") or []:
                if not isinstance(clip_raw, dict):
                    continue
                connected = str(_param_value(clip_raw.get("connected")) or "")
                if connected.startswith("Connected"):  # "Connected" or "Connected & previewing"
                    active = True
                    playing_name = _param_value(clip_raw.get("name"))
                    break
            record.layers.append(ResolumeLayerStatus(
                name=str(name) if name is not None else None,
                playing_clip_name=str(playing_name) if playing_name is not None else None,
                active=active,
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
