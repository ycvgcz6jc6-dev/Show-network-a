"""Phase C11 (rapport maître, S101): 'Développer réellement: ...
temperature...'. GigaCoreMonitor (gigacore.py) already reports
temperature for Luminex hardware via its own private enterprise OID --
this module covers everyone else, using the standard, vendor-neutral
ENTITY-SENSOR-MIB (RFC 3433), which any switch exposing hardware sensors
through the standard Entity MIB framework can answer regardless of
brand -- Aruba, Cisco, ELC or otherwise.

Every OID here was verified directly against RFC 3433's own published
text and independently cross-checked against oidref.com's per-object
pages (each showing the object's exact numeric position), not inferred
or guessed, consistent with this project's standing rule to never use an
undocumented OID.

Not every switch implements this MIB -- unlike IF-MIB, it is not
universally present. A device answering nothing here just reports no
temperature sensors, exactly like switch_monitor.py already does for
POWER-ETHERNET-MIB's single-instance PoE summary OID.
"""
from __future__ import annotations

from .snmp import async_walk, index_suffix as _index_suffix

# ENTITY-SENSOR-MIB (RFC 3433). entPhySensorTable's index is a single
# integer, entPhysicalIndex (borrowed from ENTITY-MIB's entPhysicalTable)
# -- unlike LLDP's composite index, this is as simple as IF-MIB's
# ifIndex, so the same single-suffix join logic applies.
OID_ENT_PHY_SENSOR_TYPE = "1.3.6.1.2.1.99.1.1.1.1"
OID_ENT_PHY_SENSOR_SCALE = "1.3.6.1.2.1.99.1.1.1.2"
OID_ENT_PHY_SENSOR_PRECISION = "1.3.6.1.2.1.99.1.1.1.3"
OID_ENT_PHY_SENSOR_VALUE = "1.3.6.1.2.1.99.1.1.1.4"
OID_ENT_PHY_SENSOR_OPER_STATUS = "1.3.6.1.2.1.99.1.1.1.5"

# EntitySensorDataType: only the one value this module filters for.
_SENSOR_TYPE_CELSIUS = 8

# EntitySensorDataScale: SI-prefix exponents actually plausible for a
# hardware temperature reading. A device answering with a scale outside
# this realistic range (e.g. yocto/zetta/yotta -- meaningful for other
# sensor types like power or frequency, not temperature) is reported as
# unscaled rather than guessed at.
_PLAUSIBLE_SCALE_EXPONENTS = {
    6: -9,   # nano
    7: -6,   # micro
    8: -3,   # milli
    9: 0,    # units
    10: 3,   # kilo
    11: 6,   # mega
}

# EntitySensorStatus: ok(1), unavailable(2), nonoperational(3).
_SENSOR_STATUS_LABELS = {1: "ok", 2: "unavailable", 3: "nonoperational"}


async def async_walk_temperature_sensors(host: str, community: str, *, timeout: float = 1.0,
                                          source_ip: str | None = None, max_rows: int = 128) -> list[dict]:
    """Temperature sensors (EntitySensorDataType celsius(8) only --
    voltage/current/fan-speed/other sensor types this same MIB also
    carries are not this function's concern) reported by a switch's
    standard ENTITY-SENSOR-MIB, if it implements one. Read-only GETNEXT
    walks only; nothing is ever written to a device.
    """
    sensors: dict[str, dict] = {}
    columns = {
        "type_raw": OID_ENT_PHY_SENSOR_TYPE,
        "scale_raw": OID_ENT_PHY_SENSOR_SCALE,
        "precision_raw": OID_ENT_PHY_SENSOR_PRECISION,
        "value_raw": OID_ENT_PHY_SENSOR_VALUE,
        "status_raw": OID_ENT_PHY_SENSOR_OPER_STATUS,
    }
    for field, base in columns.items():
        rows = await async_walk(host, community, base, timeout=timeout, source_ip=source_ip, max_rows=max_rows)
        for oid, value in rows:
            idx = _index_suffix(oid, base)
            if idx is None:
                continue
            sensors.setdefault(idx, {"index": idx})[field] = value

    result = []
    for idx, row in sensors.items():
        if row.get("type_raw") != _SENSOR_TYPE_CELSIUS:
            continue  # a real sensor, but not a temperature one -- not this function's concern
        value_raw = row.get("value_raw")
        precision = row.get("precision_raw")
        scale_raw = row.get("scale_raw")
        status_raw = row.get("status_raw")

        celsius = None
        if isinstance(value_raw, int) and value_raw not in (-1000000000, 1000000000):  # RFC 3433 underflow/overflow sentinels
            scale_exponent = _PLAUSIBLE_SCALE_EXPONENTS.get(scale_raw, 0 if scale_raw in (None,) else None)
            if scale_exponent is not None:
                precision_digits = precision if isinstance(precision, int) and precision >= 0 else 0
                celsius = round(value_raw * (10 ** scale_exponent) / (10 ** precision_digits), max(precision_digits, 1))

        result.append({
            "index": idx,
            "celsius": celsius,
            "status": _SENSOR_STATUS_LABELS.get(status_raw, "unknown") if isinstance(status_raw, int) else "unknown",
        })
    result.sort(key=lambda s: int(s["index"]) if str(s["index"]).isdigit() else 0)
    return result
