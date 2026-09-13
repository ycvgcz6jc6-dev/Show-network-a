from custom_components.dmx_monitor.dmx_ha_zones import DmxHAZone, DmxHAZoneEngine


def test_zone_processes_one_universe_to_multiple_lights():
    e = DmxHAZoneEngine()
    e.add(DmxHAZone("z1", "Salon", 12, ("light.a", "light.b"), "rgb", (1, 2, 3)))
    out = e.process(12, "console", bytes([255, 64, 0]))
    assert len(out) == 1
    assert out[0]["entity_id"] == ["light.a", "light.b"]
    assert out[0]["entity_count"] == 2
    assert out[0]["data"]["rgb_color"] == [255, 64, 0]


def test_zone_disabled_and_universe_isolation():
    e = DmxHAZoneEngine()
    e.add(DmxHAZone("z1", "Zone", 2, ("light.a",), "dimmer", (1,)))
    assert e.process(1, "", bytes([255])) == []
    e.zones["z1"].enabled = False
    assert e.process(2, "", bytes([255])) == []


def test_rdm_is_passive_and_gated():
    e = DmxHAZoneEngine()
    e.add(DmxHAZone("z1", "Zone", 1, ("light.a",), rdm_enabled=False))
    assert not e.observe_rdm("z1", "010203040506")
    e.zones["z1"].rdm_enabled = True
    assert e.observe_rdm("z1", "010203040506", fixture_type="RGB profile")
    assert e.rdm_snapshot()["z1"]["fixture_type"] == "RGB profile"
