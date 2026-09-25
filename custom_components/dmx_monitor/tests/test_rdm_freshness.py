import time
from custom_components.dmx_monitor.rdm_inventory import RDMInventory


def test_cached_bridge_rows_do_not_keep_rdm_device_online():
    inv = RDMInventory(stale_s=45.0)
    observed = time.time() - 120.0
    inv.ingest([{"uid": "1234:abcdef01", "device_label": "Dimmer"}], transport="RDM/OLA", observed_at=observed)
    row = inv.snapshot()["rdm_devices"][0]
    assert row["online"] is False
    assert row["stale"] is True
    assert row["age_s"] >= 119


def test_fresh_bridge_success_marks_rdm_device_online():
    inv = RDMInventory(stale_s=45.0)
    inv.ingest([{"uid": "1234:abcdef01", "device_label": "Dimmer"}], transport="RDMnet", observed_at=time.time())
    row = inv.snapshot()["rdm_devices"][0]
    assert row["online"] is True
    assert row["stale"] is False
