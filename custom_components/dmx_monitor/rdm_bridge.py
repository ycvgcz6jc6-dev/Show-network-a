"""HTTP bridge clients for RDM (OLA) and RDMnet helpers.

Bridges are optional because Home Assistant OS cannot assume the presence of
native OLA/ETCLabs libraries. All polling is read-only. Write operations are
only exposed through an explicit method and must be gated by Show Network.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.request import Request, urlopen


class RDMBridgeMonitor:
    def __init__(self, url: str, *, transport: str, timeout: float = 3.0, token: str | None = None) -> None:
        self.url = str(url or "").rstrip("/")
        self.transport = transport
        self.timeout = float(timeout)
        self.token = str(token).strip() if token else None
        self.devices: list[dict[str, Any]] = []
        self.error: str | None = None
        self.last_poll: float | None = None
        self.last_success: float | None = None
        self._task: asyncio.Task | None = None
        self.interval_s = 5.0

    @property
    def configured(self) -> bool:
        return self.url.startswith("http://") or self.url.startswith("https://")

    def _request_json(self, path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Show-Network/0.15.26"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(self.url + path, data=body, method=method, headers=headers)
        with urlopen(req, timeout=self.timeout) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("RDM bridge response too large")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("RDM bridge response must be a JSON object")
        return value

    async def start(self) -> None:
        if self.configured and self._task is None:
            self._task = asyncio.create_task(self._loop(), name=f"show-network-{self.transport.lower()}-bridge")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            await self.async_update()
            await asyncio.sleep(self.interval_s)

    async def async_update(self) -> None:
        self.last_poll = time.time()
        if not self.configured:
            self.error = None
            self.devices = []
            return
        try:
            value = await asyncio.to_thread(self._request_json, "/v1/devices")
            rows = value.get("devices", [])
            if not isinstance(rows, list):
                raise ValueError("RDM bridge devices must be a list")
            clean = []
            for row in rows:
                if isinstance(row, dict) and row.get("uid"):
                    clean.append(dict(row))
            self.devices = clean
            self.last_success = time.time()
            self.error = None
        except Exception as exc:  # helper/network failure must not break HA
            self.error = f"{type(exc).__name__}: {exc}"

    async def async_set(self, *, uid: str, universe: int | None = None, scope: str | None = None, pid: str, value: Any) -> dict:
        if not self.configured:
            raise RuntimeError(f"{self.transport} bridge is not configured")
        payload = {"uid": uid, "pid": str(pid), "value": value}
        if universe is not None:
            payload["universe"] = int(universe)
        if scope:
            payload["scope"] = str(scope)
        return await asyncio.to_thread(self._request_json, "/v1/set", method="POST", payload=payload)

    def snapshot(self) -> dict[str, Any]:
        prefix = "rdmnet_bridge" if self.transport == "RDMnet" else "rdm_bridge"
        return {
            f"{prefix}_configured": self.configured,
            f"{prefix}_error": self.error,
            f"{prefix}_last_poll": self.last_poll,
            f"{prefix}_last_success": self.last_success,
            f"{prefix}_devices": list(self.devices),
        }
