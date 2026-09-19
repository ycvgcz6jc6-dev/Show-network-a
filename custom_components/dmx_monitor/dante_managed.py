"""Read-only Dante Managed API client (Dante Director / DDM >= 1.5).

Only documented GraphQL queries are used. No mutation is implemented here.
"""
from __future__ import annotations

import time

DOMAINS_QUERY = """query Domains { domains { id name status { clocking connectivity latency subscriptions summary } } }"""
DEVICES_QUERY = """query Devices($domainId: ID!) { domain(id: $domainId) { devices { id name status { connectivity subscriptions } rxChannels { id index name subscribedDevice subscribedChannel status } txChannels { id index name } } } }"""


class DanteManagedMonitor:
    def __init__(self, session, url: str, api_key: str, domain_id: str = "") -> None:
        self.session = session
        self.url = (url or "").strip()
        self.api_key = (api_key or "").strip()
        self.domain_id = (domain_id or "").strip()
        self.data: dict = {"configured": bool(self.url and self.api_key), "available": False, "read_only": True}

    async def _query(self, query: str, variables: dict | None = None) -> dict:
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        async with self.session.post(self.url, json={"query": query, "variables": variables or {}}, headers=headers, timeout=8) as response:
            response.raise_for_status()
            payload = await response.json()
            if payload.get("errors"):
                raise RuntimeError(str(payload["errors"])[:500])
            return payload.get("data") or {}

    async def async_update(self) -> None:
        if not self.url or not self.api_key:
            self.data = {"configured": False, "available": False, "read_only": True, "reason": "Dante Managed API not configured"}
            return
        try:
            domains_data = await self._query(DOMAINS_QUERY)
            domains = domains_data.get("domains") or []
            selected = next((d for d in domains if str(d.get("id")) == self.domain_id), None) if self.domain_id else (domains[0] if len(domains) == 1 else None)
            domain_id = str(selected.get("id")) if selected else self.domain_id
            devices = []
            if domain_id:
                device_data = await self._query(DEVICES_QUERY, {"domainId": domain_id})
                devices = ((device_data.get("domain") or {}).get("devices") or [])
            subscriptions = []
            broken = []
            for dev in devices:
                for rx in dev.get("rxChannels") or []:
                    src_dev, src_ch = rx.get("subscribedDevice"), rx.get("subscribedChannel")
                    if not src_dev and not src_ch:
                        continue
                    row = {"receiver_device": dev.get("name"), "receiver_device_id": dev.get("id"), "rx_index": rx.get("index"), "rx_channel": rx.get("name"), "source_device": src_dev, "source_channel": src_ch, "status": rx.get("status")}
                    subscriptions.append(row)
                    status = str(rx.get("status") or "").lower()
                    if status and status not in {"ok", "connected", "active", "subscribed", "resolved"}:
                        broken.append(row)
            self.data = {"configured": True, "available": True, "read_only": True, "source": "Dante Managed API", "observed_at": time.time(), "domains": domains, "selected_domain_id": domain_id or None, "selected_domain_name": selected.get("name") if selected else None, "domain_status": selected.get("status") if selected else None, "devices": devices, "device_count": len(devices), "subscriptions": subscriptions, "subscription_count": len(subscriptions), "subscription_issues": broken, "subscription_issue_count": len(broken)}
        except Exception as exc:
            self.data = {"configured": True, "available": False, "read_only": True, "source": "Dante Managed API", "error": str(exc)[:500]}

    def snapshot(self) -> dict:
        return dict(self.data)
