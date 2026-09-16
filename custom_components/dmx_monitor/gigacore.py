"""Read-only GigaCore SNMP telemetry."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from .snmp import async_get

GIGACORE_TEMP_OID = "1.3.6.1.4.1.4413.1.1.43.1.8.1.5.1.0"
SYSNAME_OID = "1.3.6.1.2.1.1.5.0"
SYSUPTIME_OID = "1.3.6.1.2.1.1.3.0"
CPU_UTIL_OID = "1.3.6.1.4.1.4413.1.1.1.1.4.9.0"

@dataclass
class GigaCoreStatus:
    host: str
    sysname: str | None = None
    temperature_c: float | None = None
    cpu_percent: float | None = None
    uptime_seconds: float | None = None
    reachable: bool = False
    error: str | None = None

class GigaCoreMonitor:
    """Poll only documented/configured SNMP OIDs; never performs SET/WALK."""
    def __init__(self, hosts: list[str], community: str):
        self.hosts = hosts
        self.community = community
        self.status: dict[str, GigaCoreStatus] = {h: GigaCoreStatus(host=h) for h in hosts}
        self.temperatures: dict[str, float | None] = {h: None for h in hosts}

    async def async_update(self):
        if not self.hosts:
            return
        async def poll(host: str):
            values = await asyncio.gather(
                async_get(host, self.community, GIGACORE_TEMP_OID),
                async_get(host, self.community, SYSNAME_OID),
                async_get(host, self.community, SYSUPTIME_OID),
                async_get(host, self.community, CPU_UTIL_OID),
                return_exceptions=True,
            )
            return host, values
        results = await asyncio.gather(*(poll(h) for h in self.hosts), return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                continue
            host, values = result
            temp, sysname, uptime, cpu = values
            status = self.status.setdefault(host, GigaCoreStatus(host=host))
            status.reachable = not isinstance(temp, Exception) and any(v is not None and not isinstance(v, Exception) for v in values)
            status.error = None if status.reachable else "Aucune réponse SNMP exploitable"
            status.temperature_c = None if isinstance(temp, Exception) or temp is None else float(temp) / 10.0
            status.sysname = None if isinstance(sysname, Exception) or sysname is None else str(sysname)
            status.uptime_seconds = None if isinstance(uptime, Exception) or uptime is None else float(uptime) / 100.0
            status.cpu_percent = None if isinstance(cpu, Exception) or cpu is None else float(cpu)
            self.temperatures[host] = status.temperature_c

    def snapshot(self) -> dict[str, dict]:
        return {host: vars(status).copy() for host, status in self.status.items()}
