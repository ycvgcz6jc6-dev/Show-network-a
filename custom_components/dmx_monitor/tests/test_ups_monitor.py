import pytest
from custom_components.dmx_monitor import ups_monitor as mod


@pytest.mark.asyncio
async def test_ups_full_standard_snapshot_and_units(monkeypatch):
    values = {
        mod.OID_IDENT_MANUFACTURER: "Eaton", mod.OID_IDENT_MODEL: "9PX",
        mod.OID_IDENT_NAME: "UPS-Regie", mod.OID_BATTERY_STATUS: 2,
        mod.OID_SECONDS_ON_BATTERY: 0, mod.OID_ESTIMATED_MINUTES_REMAINING: 47,
        mod.OID_ESTIMATED_CHARGE_REMAINING: 96, mod.OID_BATTERY_VOLTAGE: 536,
        mod.OID_OUTPUT_SOURCE: 3,
    }
    async def fake_get(host, community, oid): return values[oid]
    monkeypatch.setattr(mod, "async_get", fake_get)
    m = mod.UpsMonitor(["10.2.1.10"], "public")
    await m.async_update()
    u = m.status["10.2.1.10"]
    assert u.online and u.battery_status == "normal" and u.output_source == "normal"
    assert u.battery_voltage_v == 53.6 and u.estimated_charge_remaining_pct == 96
    assert m.snapshot()["ups_online"] == 1


@pytest.mark.asyncio
async def test_ups_partial_reply_is_online_but_unknown_fields_stay_unknown(monkeypatch):
    async def fake_get(host, community, oid):
        if oid == mod.OID_IDENT_MANUFACTURER: return "APC"
        raise TimeoutError()
    monkeypatch.setattr(mod, "async_get", fake_get)
    m = mod.UpsMonitor(["10.2.1.11"], "public")
    await m.async_update()
    u = m.status["10.2.1.11"]
    assert u.online and u.manufacturer == "APC"
    assert u.battery_status is None and u.output_source is None and u.battery_voltage_v is None


@pytest.mark.asyncio
async def test_ups_no_reply_clears_previous_values_instead_of_stale_ok(monkeypatch):
    state = {"up": True}
    async def fake_get(host, community, oid):
        if not state["up"]: raise TimeoutError()
        return 5 if oid == mod.OID_OUTPUT_SOURCE else (3 if oid == mod.OID_BATTERY_STATUS else 1)
    monkeypatch.setattr(mod, "async_get", fake_get)
    m = mod.UpsMonitor(["10.2.1.12"], "public")
    await m.async_update()
    assert m.status["10.2.1.12"].online
    assert m.status["10.2.1.12"].output_source == "battery"
    state["up"] = False
    await m.async_update()
    u = m.status["10.2.1.12"]
    assert not u.online and u.output_source is None and u.battery_status is None
    assert "No response" in u.last_error


@pytest.mark.asyncio
async def test_ups_low_and_on_battery_counters(monkeypatch):
    async def fake_get(host, community, oid):
        if oid == mod.OID_BATTERY_STATUS: return 3
        if oid == mod.OID_OUTPUT_SOURCE: return 5
        return None
    monkeypatch.setattr(mod, "async_get", fake_get)
    m = mod.UpsMonitor(["10.2.1.13"], "public")
    await m.async_update()
    snap = m.snapshot()
    assert snap["ups_on_battery"] == 1 and snap["ups_battery_low"] == 1


@pytest.mark.asyncio
async def test_ups_invalid_enum_and_voltage_do_not_invent_values(monkeypatch):
    async def fake_get(host, community, oid):
        if oid == mod.OID_IDENT_NAME: return "UPS"
        if oid == mod.OID_BATTERY_STATUS: return 99
        if oid == mod.OID_OUTPUT_SOURCE: return "bad"
        if oid == mod.OID_BATTERY_VOLTAGE: return "bad"
        return None
    monkeypatch.setattr(mod, "async_get", fake_get)
    m = mod.UpsMonitor(["10.2.1.14"], "public")
    await m.async_update()
    u = m.status["10.2.1.14"]
    assert u.online and u.battery_status is None and u.output_source is None and u.battery_voltage_v is None
