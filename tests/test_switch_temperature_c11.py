"""Phase C11 (rapport maître, S101): switch temperature via the standard
ENTITY-SENSOR-MIB (RFC 3433) for non-Luminex switches (GigaCoreMonitor
already covers Luminex via its own private OID). async_walk() itself is
trusted/already exercised elsewhere; these tests cover the scale/
precision interpretation and celsius(8) filtering logic.
"""
from __future__ import annotations

import pytest

from custom_components.dmx_monitor import switch_temperature as temp

pytestmark = pytest.mark.asyncio


def _fake_walk(table: dict[str, list[tuple[str, object]]]):
    async def fake(host, community, base_oid, *, timeout=1.0, source_ip=None, max_rows=128):
        return table.get(base_oid.strip("."), [])
    return fake


async def test_rfc_3433_worked_example_25_degrees(monkeypatch):
    """RFC 3433's own example: '0 to 100 C in 0.1 increments... Precision
    of 1, Scale of units, Value ranging 0 to 1000... interpreted as
    (degrees C * 10)'. value_raw=250 must resolve to 25.0 C exactly."""
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [(f"{temp.OID_ENT_PHY_SENSOR_TYPE}.1", 8)],  # celsius(8)
        temp.OID_ENT_PHY_SENSOR_SCALE: [(f"{temp.OID_ENT_PHY_SENSOR_SCALE}.1", 9)],  # units(9)
        temp.OID_ENT_PHY_SENSOR_PRECISION: [(f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.1", 1)],
        temp.OID_ENT_PHY_SENSOR_VALUE: [(f"{temp.OID_ENT_PHY_SENSOR_VALUE}.1", 250)],
        temp.OID_ENT_PHY_SENSOR_OPER_STATUS: [(f"{temp.OID_ENT_PHY_SENSOR_OPER_STATUS}.1", 1)],  # ok(1)
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert sensors == [{"index": "1", "celsius": 25.0, "status": "ok"}]


async def test_whole_degree_no_precision(monkeypatch):
    """precision=0, scale=units: the raw value already IS whole degrees."""
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [(f"{temp.OID_ENT_PHY_SENSOR_TYPE}.1", 8)],
        temp.OID_ENT_PHY_SENSOR_SCALE: [(f"{temp.OID_ENT_PHY_SENSOR_SCALE}.1", 9)],
        temp.OID_ENT_PHY_SENSOR_PRECISION: [(f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.1", 0)],
        temp.OID_ENT_PHY_SENSOR_VALUE: [(f"{temp.OID_ENT_PHY_SENSOR_VALUE}.1", 42)],
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert sensors[0]["celsius"] == 42.0


async def test_non_temperature_sensors_are_excluded(monkeypatch):
    """A device with e.g. a voltage sensor (type 4) and PSU fan-speed
    sensor (rpm, type 10) alongside a real temperature sensor must only
    report the temperature one -- this function is not a generic sensor
    dump."""
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [
            (f"{temp.OID_ENT_PHY_SENSOR_TYPE}.1", 8),   # celsius -- keep
            (f"{temp.OID_ENT_PHY_SENSOR_TYPE}.2", 4),   # voltsDC -- drop
            (f"{temp.OID_ENT_PHY_SENSOR_TYPE}.3", 10),  # rpm -- drop
        ],
        temp.OID_ENT_PHY_SENSOR_SCALE: [(f"{temp.OID_ENT_PHY_SENSOR_SCALE}.1", 9)],
        temp.OID_ENT_PHY_SENSOR_PRECISION: [(f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.1", 0)],
        temp.OID_ENT_PHY_SENSOR_VALUE: [
            (f"{temp.OID_ENT_PHY_SENSOR_VALUE}.1", 38),
            (f"{temp.OID_ENT_PHY_SENSOR_VALUE}.2", 3300),
            (f"{temp.OID_ENT_PHY_SENSOR_VALUE}.3", 4500),
        ],
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert len(sensors) == 1
    assert sensors[0]["index"] == "1"
    assert sensors[0]["celsius"] == 38.0


async def test_overflow_sentinel_reports_none_not_a_bogus_number(monkeypatch):
    """RFC 3433: '+1000000000 indicates an overflow error' -- must never
    be reported as a literal (absurd) temperature."""
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [(f"{temp.OID_ENT_PHY_SENSOR_TYPE}.1", 8)],
        temp.OID_ENT_PHY_SENSOR_SCALE: [(f"{temp.OID_ENT_PHY_SENSOR_SCALE}.1", 9)],
        temp.OID_ENT_PHY_SENSOR_PRECISION: [(f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.1", 0)],
        temp.OID_ENT_PHY_SENSOR_VALUE: [(f"{temp.OID_ENT_PHY_SENSOR_VALUE}.1", 1000000000)],
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert sensors[0]["celsius"] is None


async def test_nonoperational_sensor_status_reported(monkeypatch):
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [(f"{temp.OID_ENT_PHY_SENSOR_TYPE}.1", 8)],
        temp.OID_ENT_PHY_SENSOR_OPER_STATUS: [(f"{temp.OID_ENT_PHY_SENSOR_OPER_STATUS}.1", 3)],  # nonoperational
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert sensors[0]["status"] == "nonoperational"


async def test_device_with_no_entity_sensor_mib_returns_empty_list(monkeypatch):
    """Not every switch implements this MIB -- must degrade to an empty
    list, not an error, exactly like the rest of this codebase treats an
    unimplemented-but-standard MIB."""
    monkeypatch.setattr(temp, "async_walk", _fake_walk({}))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    assert sensors == []


async def test_multiple_temperature_sensors_sorted_by_index(monkeypatch):
    table = {
        temp.OID_ENT_PHY_SENSOR_TYPE: [
            (f"{temp.OID_ENT_PHY_SENSOR_TYPE}.10", 8),
            (f"{temp.OID_ENT_PHY_SENSOR_TYPE}.2", 8),
        ],
        temp.OID_ENT_PHY_SENSOR_SCALE: [
            (f"{temp.OID_ENT_PHY_SENSOR_SCALE}.10", 9), (f"{temp.OID_ENT_PHY_SENSOR_SCALE}.2", 9),
        ],
        temp.OID_ENT_PHY_SENSOR_PRECISION: [
            (f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.10", 0), (f"{temp.OID_ENT_PHY_SENSOR_PRECISION}.2", 0),
        ],
        temp.OID_ENT_PHY_SENSOR_VALUE: [
            (f"{temp.OID_ENT_PHY_SENSOR_VALUE}.10", 50), (f"{temp.OID_ENT_PHY_SENSOR_VALUE}.2", 30),
        ],
    }
    monkeypatch.setattr(temp, "async_walk", _fake_walk(table))
    sensors = await temp.async_walk_temperature_sensors("10.4.1.4", "public")
    # Numeric sort (2 before 10), matching the same convention as
    # switch_port_telemetry.py's port ordering.
    assert [s["index"] for s in sensors] == ["2", "10"]
