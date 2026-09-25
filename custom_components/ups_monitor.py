"""Passive UPS (Uninterruptible Power Supply) supervision via UPS-MIB.

Uses RFC 1628 (IETF, May 1994), a vendor-neutral standard MIB implemented
by essentially every networked UPS with an SNMP card (APC AP96xx/NMC,
Eaton Network-M2, CyberPower RMCARD, Vertiv/Liebert IS-UNITY, Tripp Lite
SNMPWEBCARD, etc). Every OID below is the real, standard OID -- verified
directly against the RFC text (and, for upsOutputSource, against the
official published erratum eid4831 correcting a typo in the RFC's own
compliance statement).

Deliberately scoped to the Ident and Battery groups only, which are all
scalar OIDs (a single GET each). The Input/Output/Bypass groups in the
real MIB are SNMP TABLES indexed by line number (a UPS can have more than
one input/output line) -- reading those correctly requires either an
SNMP walk or knowing the real index in advance, and guessing an index
without a real UPS to verify against risks silently reading the wrong
line, or a line that doesn't exist. Read-only: this module has no SET
capability by design, matching this project's supervision-only stance
wherever a "control the mains" style action would be materially higher
risk than any other passive monitor here.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, asdict
from typing import Any

from .snmp import async_get

# UPS-MIB (RFC 1628) -- confirmed OIDs, scalar objects only.
OID_IDENT_MANUFACTURER = "1.3.6.1.2.1.33.1.1.1"
OID_IDENT_MODEL = "1.3.6.1.2.1.33.1.1.2"
OID_IDENT_NAME = "1.3.6.1.2.1.33.1.1.5"
OID_BATTERY_STATUS = "1.3.6.1.2.1.33.1.2.1"
OID_SECONDS_ON_BATTERY = "1.3.6.1.2.1.33.1.2.2"
OID_ESTIMATED_MINUTES_REMAINING = "1.3.6.1.2.1.33.1.2.3"
OID_ESTIMATED_CHARGE_REMAINING = "1.3.6.1.2.1.33.1.2.4"
OID_BATTERY_VOLTAGE = "1.3.6.1.2.1.33.1.2.5"
# upsOutputSource is a scalar (not table-indexed) despite living under the
# Output group -- confirmed by its OID depth (upsObjects.4.1, not .4.<table>.1.<n>)
# and its OBJECT-TYPE definition. Enum per the RFC text and errata eid4831:
OID_OUTPUT_SOURCE = "1.3.6.1.2.1.33.1.4.1"

BATTERY_STATUS_LABELS = {1: "unknown", 2: "normal", 3: "low", 4: "depleted"}
OUTPUT_SOURCE_LABELS = {1: "other", 2: "none", 3: "normal", 4: "bypass", 5: "battery", 6: "booster", 7: "reducer"}


@dataclass
class UpsStatus:
    host: str
    online: bool = False
    last_error: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    name: str | None = None
    battery_status: str | None = None
    on_battery_seconds: int | None = None
    estimated_minutes_remaining: int | None = None
    estimated_charge_remaining_pct: int | None = None
    battery_voltage_v: float | None = None  # UPS-MIB reports in 0.1V units; converted here
    output_source: str | None = None

    def public(self) -> dict[str, Any]:
        return asdict(self)


class UpsMonitor:
    """Poll one or more UPS devices' standard UPS-MIB (RFC 1628) scalars."""

    def __init__(self, hosts: list[str], community: str) -> None:
        self.hosts = list(dict.fromkeys(h.strip() for h in hosts if h.strip()))
        self.community = community
        self.status: dict[str, UpsStatus] = {h: UpsStatus(host=h) for h in self.hosts}

    async def _poll_one(self, host: str) -> UpsStatus:
        status = UpsStatus(host=host)

        async def get(oid: str):
            try:
                return await async_get(host, self.community, oid)
            except Exception:
                return None

        (manufacturer, model, name, battery_status, on_battery_s,
         minutes_remaining, charge_pct, battery_v, output_source) = await asyncio.gather(
            get(OID_IDENT_MANUFACTURER), get(OID_IDENT_MODEL), get(OID_IDENT_NAME),
            get(OID_BATTERY_STATUS), get(OID_SECONDS_ON_BATTERY),
            get(OID_ESTIMATED_MINUTES_REMAINING), get(OID_ESTIMATED_CHARGE_REMAINING),
            get(OID_BATTERY_VOLTAGE), get(OID_OUTPUT_SOURCE),
        )

        # Any single successful reply is enough to call the device "online";
        # a real UPS-MIB agent answering a GET at all confirms it exists and
        # speaks this MIB, even if a specific optional scalar isn't supported.
        replies = (manufacturer, model, name, battery_status, on_battery_s, minutes_remaining, charge_pct, battery_v, output_source)
        status.online = any(r is not None for r in replies)
        if not status.online:
            status.last_error = "No response to UPS-MIB (RFC 1628) queries"
            return status

        status.manufacturer = str(manufacturer) if manufacturer is not None else None
        status.model = str(model) if model is not None else None
        status.name = str(name) if name is not None else None
        try:
            status.battery_status = BATTERY_STATUS_LABELS.get(int(battery_status)) if battery_status is not None else None
        except (TypeError, ValueError):
            status.battery_status = None
        try:
            status.on_battery_seconds = int(on_battery_s) if on_battery_s is not None else None
        except (TypeError, ValueError):
            status.on_battery_seconds = None
        try:
            status.estimated_minutes_remaining = int(minutes_remaining) if minutes_remaining is not None else None
        except (TypeError, ValueError):
            status.estimated_minutes_remaining = None
        try:
            status.estimated_charge_remaining_pct = int(charge_pct) if charge_pct is not None else None
        except (TypeError, ValueError):
            status.estimated_charge_remaining_pct = None
        try:
            # upsBatteryVoltage is in units of 0.1 Volts DC per the RFC.
            status.battery_voltage_v = round(int(battery_v) / 10.0, 1) if battery_v is not None else None
        except (TypeError, ValueError):
            status.battery_voltage_v = None
        try:
            status.output_source = OUTPUT_SOURCE_LABELS.get(int(output_source)) if output_source is not None else None
        except (TypeError, ValueError):
            status.output_source = None
        return status

    async def async_update(self) -> None:
        results = await asyncio.gather(*(self._poll_one(h) for h in self.hosts), return_exceptions=True)
        for host, result in zip(self.hosts, results):
            self.status[host] = result if isinstance(result, UpsStatus) else UpsStatus(host=host, last_error=str(result))

    def snapshot(self) -> dict[str, Any]:
        units = [s.public() for s in self.status.values()]
        return {
            "ups_units": units,
            "ups_total": len(units),
            "ups_online": sum(1 for u in units if u["online"]),
            "ups_on_battery": sum(1 for u in units if u["output_source"] == "battery"),
            "ups_battery_low": sum(1 for u in units if u["battery_status"] in ("low", "depleted")),
        }
