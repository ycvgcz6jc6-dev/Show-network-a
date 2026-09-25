"""Read-only rack PDU (Power Distribution Unit) outlet-status monitor
for the two most common vendors -- APC (by Schneider Electric) and
Raritan (Dominion PX2) -- via SNMP.

WHY TWO VENDORS, EXPLICITLY CHOSEN PER HOST, NOT AUTO-DETECTED:
Unlike IF-MIB or ENTITY-SENSOR-MIB (C11), there is no single,
vendor-neutral standard PDU MIB in practical use. Every vendor
publishes its own proprietary tree -- confirmed by every independent
source checked (Schneider Electric's own support pages, Raritan's own
MIB, and Network UPS Tools' own driver-per-vendor architecture, which
ships a *separate* subdriver file for essentially every PDU vendor:
apc-pdu-mib.c, raritan-pdu-mib.c, raritan-px2-mib.c, hpe-pdu-mib.c,
eaton-pdu-marlin-mib.c, and more). Auto-detecting which proprietary
tree a given host speaks would itself be guessing; the vendor is a
required, explicit per-host setting instead.

OIDs below are taken directly from Network UPS Tools' own open-source,
production driver source
(github.com/networkupstools/nut/blob/master/drivers/apc-pdu-mib.c and
.../raritan-px2-mib.c) -- not inferred from a MIB browser description,
not guessed. NUT is itself real, widely-deployed monitoring software
tested against real hardware, the same standard of evidence already
applied to Nexus Audio's source code and CEM3's real captured pages
elsewhere in this project.

APC ALSO HAS MULTIPLE GENERATIONS WITH DIFFERENT MIB SUBTREES (rPDU for
the older AP7xxx series, rPDU2 for the newer "2G" AP84xx/86xx/88xx/89xx
series, confirmed independently by Schneider Electric's own support
articles) -- NUT's apc-pdu-mib.c driver uses the OLDER "sPDU"/rPDU
tree's outlet-control OIDs (1.3.6.1.4.1.318.1.1.4.4.x), which is the
tree this module uses too, matching the verified source exactly rather
than attempting the newer rPDU2 tree without the same level of direct
confirmation.

DELIBERATELY MONITORING-ONLY. Both vendors' own outlet-status OIDs are
read-write (the same OID that reports on/off can also be SET to switch
an outlet) -- this module only ever sends a GET, never a SET, matching
this project's "read first, control behind Active Control" rule
applied identically to every other adapter in this codebase.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .snmp import async_get, async_walk

# --- APC (PowerNet-MIB), verified against apc-pdu-mib.c -------------------
APC_OID_MODEL = "1.3.6.1.4.1.318.1.1.4.1.4.0"       # sPDUIdentModelNumber
APC_OID_SERIAL = "1.3.6.1.4.1.318.1.1.4.1.5.0"      # sPDUIdentSerialNumber
APC_OID_FIRMWARE = "1.3.6.1.4.1.318.1.1.4.1.2.0"    # sPDUIdentHardwareRev
APC_OID_OUTLET_COUNT = "1.3.6.1.4.1.318.1.1.4.4.1.0"  # sPDUOutletConfigNumOutlets
APC_OID_OUTLET_DESC = "1.3.6.1.4.1.318.1.1.4.4.2.1.4"  # sPDUOutletConfigTableName (indexed)
APC_OID_OUTLET_STATUS = "1.3.6.1.4.1.318.1.1.4.4.2.1.3"  # sPDUOutletCtl (indexed) -- GET only, never SET here
_APC_OUTLET_STATUS_LABELS = {1: "on", 2: "off"}  # outletOn(1)/outletOff(2), verified against NUT's own lookup table

# --- Raritan (PX2-MIB), verified against raritan-px2-mib.c -----------------
RARITAN_OID_MFR = "1.3.6.1.4.1.13742.6.3.2.1.1.2.1"
RARITAN_OID_MODEL = "1.3.6.1.4.1.13742.6.3.2.1.1.3.1"
RARITAN_OID_SERIAL = "1.3.6.1.4.1.13742.6.3.2.1.1.4.1"
RARITAN_OID_OUTLET_COUNT = "1.3.6.1.4.1.13742.6.3.2.2.1.4.1"
RARITAN_OID_OUTLET_DESC = "1.3.6.1.4.1.13742.6.3.5.3.1.3.1"    # indexed
RARITAN_OID_OUTLET_STATUS = "1.3.6.1.4.1.13742.6.4.1.2.1.3.1"  # indexed -- GET only, never SET here
# Raritan's status OID is a shared "sensor state" enum reused across many
# sensor types; only the two values relevant to an outlet's on/off state
# are interpreted here (7=on, 8=off per NUT's own full lookup table).
_RARITAN_OUTLET_STATUS_LABELS = {7: "on", 8: "off"}

SUPPORTED_VENDORS = ("apc", "raritan")


@dataclass
class PDUOutletStatus:
    index: str
    name: str | None = None
    state: str | None = None  # "on" / "off" / "unknown"


@dataclass
class PDURecord:
    host: str
    vendor: str
    online: bool = False
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    outlets: list[PDUOutletStatus] = field(default_factory=list)
    last_poll: float | None = None
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "host": self.host, "vendor": self.vendor, "online": self.online,
            "model": self.model, "serial": self.serial, "firmware": self.firmware,
            "outlet_count": len(self.outlets),
            "outlets_on": sum(1 for o in self.outlets if o.state == "on"),
            "outlets": [{"index": o.index, "name": o.name, "state": o.state} for o in self.outlets],
            "last_poll": self.last_poll, "error": self.error,
            "protocol": f"SNMP ({self.vendor}), OIDs verified against Network UPS Tools' own driver source",
            "scope": "status_only_no_outlet_control",
        }


class PDUMonitor:
    """Polls outlet status for a set of configured PDU hosts. Each host
    has an explicit, user-specified vendor ("apc" or "raritan") -- never
    auto-detected. Read-only: only ever sends SNMP GET/GETNEXT, never SET.
    """

    def __init__(self, hosts: dict[str, str], community: str = "public", *, timeout: float = 1.5):
        """hosts: {ip: vendor}, vendor one of SUPPORTED_VENDORS."""
        self.hosts = {ip: v for ip, v in hosts.items() if v in SUPPORTED_VENDORS}
        self.community = community
        self.timeout = timeout
        self.records: dict[str, PDURecord] = {}

    async def _poll_apc(self, host: str) -> PDURecord:
        record = PDURecord(host=host, vendor="apc", last_poll=time.time())
        model = await async_get(host, self.community, APC_OID_MODEL, timeout=self.timeout)
        if model is None:
            record.online = False
            record.error = "no reply to sPDUIdentModelNumber"
            return record
        record.online = True
        record.model = str(model)
        record.serial = str(await async_get(host, self.community, APC_OID_SERIAL, timeout=self.timeout) or "") or None
        record.firmware = str(await async_get(host, self.community, APC_OID_FIRMWARE, timeout=self.timeout) or "") or None

        desc_rows = await async_walk(host, self.community, APC_OID_OUTLET_DESC, timeout=self.timeout)
        status_rows = await async_walk(host, self.community, APC_OID_OUTLET_STATUS, timeout=self.timeout)
        names = {oid.rsplit(".", 1)[-1]: val for oid, val in desc_rows}
        for oid, raw_status in status_rows:
            idx = oid.rsplit(".", 1)[-1]
            record.outlets.append(PDUOutletStatus(
                index=idx, name=str(names.get(idx)) if idx in names else None,
                state=_APC_OUTLET_STATUS_LABELS.get(raw_status, "unknown") if isinstance(raw_status, int) else "unknown",
            ))
        record.outlets.sort(key=lambda o: int(o.index) if o.index.isdigit() else 0)
        return record

    async def _poll_raritan(self, host: str) -> PDURecord:
        record = PDURecord(host=host, vendor="raritan", last_poll=time.time())
        model = await async_get(host, self.community, RARITAN_OID_MODEL, timeout=self.timeout)
        if model is None:
            record.online = False
            record.error = "no reply to model OID"
            return record
        record.online = True
        record.model = str(model)
        record.serial = str(await async_get(host, self.community, RARITAN_OID_SERIAL, timeout=self.timeout) or "") or None

        desc_rows = await async_walk(host, self.community, RARITAN_OID_OUTLET_DESC, timeout=self.timeout)
        status_rows = await async_walk(host, self.community, RARITAN_OID_OUTLET_STATUS, timeout=self.timeout)
        names = {oid.rsplit(".", 1)[-1]: val for oid, val in desc_rows}
        for oid, raw_status in status_rows:
            idx = oid.rsplit(".", 1)[-1]
            record.outlets.append(PDUOutletStatus(
                index=idx, name=str(names.get(idx)) if idx in names else None,
                state=_RARITAN_OUTLET_STATUS_LABELS.get(raw_status, "unknown") if isinstance(raw_status, int) else "unknown",
            ))
        record.outlets.sort(key=lambda o: int(o.index) if o.index.isdigit() else 0)
        return record

    async def _poll_one(self, host: str, vendor: str) -> PDURecord:
        try:
            if vendor == "apc":
                return await self._poll_apc(host)
            return await self._poll_raritan(host)
        except Exception as err:  # noqa: BLE001 - SNMP timeouts/malformed replies can raise many distinct types
            record = PDURecord(host=host, vendor=vendor, last_poll=time.time())
            record.online = False
            record.error = f"{type(err).__name__}: {err}"
            return record

    async def async_update(self) -> None:
        if not self.hosts:
            return
        import asyncio
        results = await asyncio.gather(*(self._poll_one(h, v) for h, v in self.hosts.items()), return_exceptions=True)
        for host, result in zip(self.hosts, results):
            if isinstance(result, Exception):
                continue
            self.records[host] = result

    def snapshot(self) -> list[dict]:
        return [rec.snapshot() for rec in self.records.values()]
