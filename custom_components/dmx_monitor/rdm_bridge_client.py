"""Read-only HTTP bridge client for RDM (OLA) / RDMnet gateways.

const.py declares CONF_RDM_BRIDGE_URL and CONF_RDMNET_BRIDGE_URL as plain
URLs, the same shape as CONF_AVDECC_BRIDGE_URL -- confirming RDM/RDMnet are
meant to be consumed the same way AVDECC already is: a small external
helper (an OLA (Open Lighting Architecture) instance's HTTP API, or a
vendor RDMnet gateway's own JSON endpoint) that this integration polls
read-only, never a from-scratch RDM stack implemented in this codebase.

Expected GET endpoint response (minimum):
{
  "devices": [{
    "uid": "7a70:00000001", "manufacturer": "Robe", "model": "MegaPointe",
    "label": "SL FOH 1", "dmx_address": 1, "footprint": 40,
    "personality": 3, "personality_count": 8, "sensors": [...]
  }]
}

Only keys explicitly returned by the bridge are exposed as telemetry;
nothing here talks RDM/RDMnet itself.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.request import Request, urlopen

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class RDMBridgeMonitor:
    """Polls one RDM (OLA) or RDMnet bridge HTTP endpoint.

    ``transport`` is a free-text label (e.g. "RDM/OLA" or "RDMnet") passed
    straight through to RDMInventory.ingest() by whoever wires this up, so
    one class serves both CONF_RDM_BRIDGE_URL and CONF_RDMNET_BRIDGE_URL.
    """

    def __init__(self, endpoint: str, *, transport: str = "RDM", interval_s: float = 5.0, timeout_s: float = 2.5) -> None:
        self.endpoint = (endpoint or "").strip()
        self.transport = transport
        self.interval_s = float(interval_s)
        self.timeout_s = float(timeout_s)
        self.devices: list[dict[str, Any]] = []
        self.last_error: str | None = None
        self.last_poll: float | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if not self.endpoint:
            return
        self._task = asyncio.create_task(self._loop(), name=f"show-network-{self.transport.lower().replace('/', '-')}-bridge")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self.interval_s)

    def _fetch(self) -> dict[str, Any]:
        req = Request(self.endpoint, headers={"Accept": "application/json", "User-Agent": "Show-Network/0.15.2"})
        with urlopen(req, timeout=self.timeout_s) as response:  # nosec B310 - admin-configured local endpoint
            data = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(data) > _MAX_RESPONSE_BYTES:
            raise ValueError(f"{self.transport} bridge response too large")
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{self.transport} bridge payload must be an object")
        return payload

    async def poll_once(self) -> None:
        self.last_poll = time.time()
        try:
            payload = await asyncio.to_thread(self._fetch)
            devices = payload.get("devices") or []
            if not isinstance(devices, list):
                raise ValueError(f"{self.transport} bridge 'devices' must be a list")
            self.devices = [d for d in devices if isinstance(d, dict)]
            self.last_error = None
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self.last_error = f"{type(err).__name__}: {err}"

    def snapshot(self) -> dict[str, Any]:
        prefix = self.transport.lower().replace("/", "_")
        return {
            f"{prefix}_bridge_configured": bool(self.endpoint),
            f"{prefix}_bridge_error": self.last_error,
            f"{prefix}_bridge_last_poll": self.last_poll,
            f"{prefix}_bridge_device_count": len(self.devices),
        }
