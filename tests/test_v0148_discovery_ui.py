from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CC=ROOT/'custom_components/dmx_monitor'

def test_network_discovery_has_all_interface_helpers():
    text=(CC/'network_discovery.py').read_text()
    assert 'def ipv4_interfaces' in text
    assert 'def warm_neighbor_cache' in text
    assert "subnet_too_large" in text

def test_manual_scan_is_active_but_periodic_scan_stays_passive():
    text=(CC/'runtime/setup.py').read_text()
    assert 'manual_scan = bool(active)' in text
    assert 'lambda: _vendor_discovery_tick(active=True)' in text
    assert 'async_track_time_interval(hass,_vendor_discovery_tick' in text

def test_module_toggle_reloads_entry():
    text=(CC/'services/configuration.py').read_text()
    assert text.count('await hass.config_entries.async_reload(entry.entry_id)') >= 2

def test_module_refresh_no_longer_rebuilds_whole_dashboard_for_live_panels():
    text=(CC/'static/show-network.js').read_text()
    assert "['audio','amplifiers','video','security','network','etc'].includes(key)" not in text
    assert 'Vue interface' in text

def test_inline_home_assistant_brand_assets_exist():
    brand=CC/'brand'
    for name in ('icon.png','icon@2x.png','logo.png','logo@2x.png'):
        assert (brand/name).is_file()
