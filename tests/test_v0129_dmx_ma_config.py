from pathlib import Path
ROOT=Path(__file__).parents[1]
def read(p): return (ROOT/p).read_text()
def test_dmx_options_are_real_runtime_settings():
    cfg=read('custom_components/dmx_monitor/config_flow.py'); rt=read('custom_components/dmx_monitor/runtime/setup.py')
    for key in ('CONF_DMX_ARTNET_ENABLED','CONF_DMX_SACN_ENABLED','CONF_DMX_SOURCE','CONF_UNIVERSES'):
        assert key in cfg and key in rt
    assert 'multicast_universes=_parse_universes' in rt
    assert 'artnet_enabled=' in rt and 'sacn_enabled=' in rt and 'source_filter=' in rt
def test_receiver_can_disable_protocols_and_filter_source():
    text=read('custom_components/dmx_monitor/lighting_receiver.py')
    assert 'if protocol == "ARTNET" and not self.artnet_enabled' in text
    assert 'if protocol == "SACN" and not self.sacn_enabled' in text
    assert 'addr[0] != self.source_filter' in text
def test_ma_has_enable_and_interface_runtime_binding():
    cfg=read('custom_components/dmx_monitor/config_flow.py'); rt=read('custom_components/dmx_monitor/runtime/setup.py')
    assert 'CONF_MA_ENABLED' in cfg
    assert 'settings.get(CONF_MA_ENABLED, True)' in rt
    assert 'interface_ma = settings.get(CONF_INTERFACE_MA, interface)' in rt

def test_options_reload_runtime():
    text=read('custom_components/dmx_monitor/__init__.py')
    assert 'entry.add_update_listener(_async_options_updated)' in text
    assert 'async_reload(entry.entry_id)' in text
