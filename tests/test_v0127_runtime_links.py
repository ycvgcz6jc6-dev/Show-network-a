from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"dmx_monitor"

def test_dmx_zone_import_uses_parent_package():
    text=(COMP/"services"/"dmx.py").read_text()
    assert "from .dmx_ha_zones import" not in text
    assert "from ..dmx_ha_zones import DmxHAZone" in text

def test_scan_network_service_and_ui_are_wired():
    dev=(COMP/"services"/"device.py").read_text()
    ui=(COMP/"static"/"show-network.js").read_text()
    assert 'async_register(DOMAIN, "scan_network"' in dev
    assert "callService('dmx_monitor','scan_network'" in ui
    assert "CONFIGURATION RÉSEAU SHOW CONTROL" in ui

def test_rule_parser_accepts_bracketed_values():
    from custom_components.dmx_monitor.rules import parse_channel_selection
    assert parse_channel_selection("[1, 2, 5-7]") == (1,2,5,6,7)
    assert parse_channel_selection([1,3,4]) == (1,3,4)
