"""Generic, standards-based SNMP switch monitor.

GigaCoreMonitor (gigacore.py) only knows Luminex's private enterprise OIDs
(temperature, CPU) -- it cannot say anything useful about any other vendor
in data/switches.yaml. This module fills that gap for every vendor that has
*no* documented private MIB in this project, by polling only OIDs from
public, vendor-neutral standard MIBs:

- SNMPv2-MIB (identity: sysDescr, sysName, sysUpTime, sysObjectID)
- IF-MIB (basic interface count via ifNumber)
- POWER-ETHERNET-MIB (PoE, RFC 3621) and Q-BRIDGE-MIB (VLAN, RFC 4363)
  single-instance summary OIDs, exposed as "documented_capability" evidence
  and only promoted to a live value if the device actually answers.

Explicitly out of scope, and *not* guessed at: any ELC- or Green-GO-branded
private enterprise MIB. A web search while building this module found no
public documentation for either. Green-GO's own manual states their
intercom devices connect through ordinary third-party managed switches
rather than a Green-GO-branded switch product, so "Green-GO" showing up
here is really whatever generic/vendor switch is hosting that intercom
traffic -- this module treats it exactly as such, with no fabricated
Green-GO-specific telemetry.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from .snmp import async_get, SNMPError

_LOGGER = logging.getLogger(__name__)

# --- SNMPv2-MIB: universal on every compliant SNMP agent -------------------
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"

# --- IF-MIB: universal on any switch ---------------------------------------
OID_IF_NUMBER = "1.3.6.1.2.1.2.1.0"

# --- POWER-ETHERNET-MIB (RFC 3621): standard, but only present if the ------
# --- device implements 802.3af/at PoE management via this MIB.            --
# pethMainPseConsumptionPower.1 (total PSE power consumption in watts, per
# power supply group 1). Many switches only expose per-port PoE via a table
# (which needs a WALK, out of scope for this GET-only module), so this
# single-instance OID is attempted as a best-effort summary only.
OID_POE_MAIN_PSE_POWER = "1.3.6.1.2.1.105.1.3.1.1.4.1"

# --- Q-BRIDGE-MIB (RFC 4363): dot1qNumVlans-equivalent is not a single ----
# --- scalar in the standard MIB, so VLAN support is reported only as a    --
# --- documented capability (see SwitchFeature below), never polled here. --

_STANDARD_OIDS = {
    "sysDescr": OID_SYS_DESCR,
    "sysObjectID": OID_SYS_OBJECT_ID,
    "sysUpTime": OID_SYS_UPTIME,
    "sysName": OID_SYS_NAME,
    "ifNumber": OID_IF_NUMBER,
}


@dataclass
class GenericSwitchStatus:
    host: str
    profile_key: str | None = None
    sys_descr: str | None = None
    sys_object_id: str | None = None
    sys_name: str | None = None
    uptime_seconds: float | None = None
    interface_count: int | None = None
    poe_total_watts: float | None = None
    reachable: bool = False
    error: str | None = None
    evidence: list[str] = field(default_factory=list)


class GenericSwitchMonitor:
    """Poll any switch profile using only public, vendor-neutral MIBs.

    Intended for every entry in switch_profiles.enabled_profiles() that has
    no dedicated vendor client (i.e. everything except Luminex/GigaCore,
    which keeps using GigaCoreMonitor for its private OIDs). This gives
    ELC and any generic/third-party switch real identity + reachability +
    uptime telemetry without guessing at undocumented vendor MIBs.
    """

    def __init__(self, hosts: dict[str, str], community: str, *, poll_poe: bool = True) -> None:
        """``hosts`` maps host/IP -> switch_profiles key (for display only)."""
        self.hosts = dict(hosts)
        self.community = community
        self.poll_poe = poll_poe
        self.status: dict[str, GenericSwitchStatus] = {
            host: GenericSwitchStatus(host=host, profile_key=profile_key)
            for host, profile_key in self.hosts.items()
        }

    async def _poll_one(self, host: str, profile_key: str | None) -> GenericSwitchStatus:
        status = GenericSwitchStatus(host=host, profile_key=profile_key)

        async def get(oid: str):
            try:
                return await async_get(host, self.community, oid)
            except SNMPError:
                return None

        results = await asyncio.gather(
            get(OID_SYS_DESCR),
            get(OID_SYS_OBJECT_ID),
            get(OID_SYS_UPTIME),
            get(OID_SYS_NAME),
            get(OID_IF_NUMBER),
        )
        sys_descr, sys_object_id, uptime, sys_name, if_number = results

        status.reachable = any(v is not None for v in results)
        status.error = None if status.reachable else "Aucune réponse SNMP exploitable"
        status.sys_descr = str(sys_descr) if sys_descr is not None else None
        status.sys_object_id = str(sys_object_id) if sys_object_id is not None else None
        status.sys_name = str(sys_name) if sys_name is not None else None
        status.uptime_seconds = float(uptime) / 100.0 if isinstance(uptime, int) else None
        status.interface_count = int(if_number) if isinstance(if_number, int) else None
        if status.sys_descr:
            status.evidence.append(f"sysDescr: {status.sys_descr}")

        if status.reachable and self.poll_poe:
            poe = await get(OID_POE_MAIN_PSE_POWER)
            if poe is not None:
                status.poe_total_watts = float(poe)
                status.evidence.append("POWER-ETHERNET-MIB pethMainPseConsumptionPower answered")

        return status

    async def async_update(self) -> None:
        if not self.hosts:
            return
        results = await asyncio.gather(
            *(self._poll_one(host, profile_key) for host, profile_key in self.hosts.items()),
            return_exceptions=True,
        )
        for host, result in zip(self.hosts, results):
            if isinstance(result, Exception):
                _LOGGER.debug("Generic switch poll failed for %s: %s", host, result)
                continue
            self.status[host] = result

    def snapshot(self) -> dict[str, dict]:
        return {
            host: {
                **vars(status),
                "capability_note": (
                    "Identity/uptime/interface-count via standard SNMPv2-MIB/IF-MIB. "
                    "PoE via POWER-ETHERNET-MIB only if the device answers it. "
                    "No vendor-private ELC or Green-GO OIDs are used: none are "
                    "publicly documented, so none are guessed at."
                ),
            }
            for host, status in self.status.items()
        }
