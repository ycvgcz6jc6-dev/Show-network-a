from pathlib import Path
from custom_components.dmx_monitor.rule_storage import RuleStore
from custom_components.dmx_monitor.dmx_ha_mapping_storage import DmxHAMappingStore


def test_rule_store_skips_identical_write(tmp_path: Path):
    store = RuleStore(str(tmp_path))
    store.save([])
    first = store.path.stat().st_mtime_ns
    store.save([])
    assert store.path.stat().st_mtime_ns == first


def test_mapping_store_skips_identical_write(tmp_path: Path):
    store = DmxHAMappingStore(str(tmp_path))
    store.save([])
    first = store.path.stat().st_mtime_ns
    store.save([])
    assert store.path.stat().st_mtime_ns == first
