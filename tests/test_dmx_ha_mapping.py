import sys
sys.path.insert(0, '/mnt/data/build160')
from custom_components.dmx_monitor.dmx_ha_mapping import DmxHAMapping, DmxHAMappingEngine

def test_dimmer():
    e=DmxHAMappingEngine(); e.add(DmxHAMapping('x',1,(1,),entity_id='light.a'))
    p=e.process(1,None,bytes([255]))
    assert p[0]['domain']=='light' and p[0]['service']=='turn_on' and p[0]['data']['brightness_pct']==100

def test_rgb():
    e=DmxHAMappingEngine(); e.add(DmxHAMapping('x',1,(1,2,3),entity_id='light.a',mode='rgb'))
    p=e.process(1,None,bytes([1,2,3])); assert p[0]['data']['rgb_color']==[1,2,3]

def test_switch():
    e=DmxHAMappingEngine(); e.add(DmxHAMapping('x',1,(1,),entity_id='light.a',mode='switch'))
    assert e.process(1,None,bytes([0]))[0]['service']=='turn_off'

def test_dimmer_curves_are_supported_and_non_linear():
    values = [64, 128, 192]
    for curve in ("linear", "gamma_1_8", "gamma_2_0", "gamma_2_2", "gamma_2_4", "logarithmic", "dali_log", "s_curve"):
        e = DmxHAMappingEngine()
        e.add(DmxHAMapping("x", 1, (1,), entity_id="light.a", dimmer_curve=curve))
        p = e.process(1, None, bytes([128]))
        assert 0 <= p[0]["data"]["brightness_pct"] <= 100


def test_dali_log_is_explicitly_non_linear():
    e = DmxHAMappingEngine()
    e.add(DmxHAMapping("x", 1, (1,), entity_id="light.a", dimmer_curve="dali_log", min_interval_ms=0))
    p = e.process(1, None, bytes([64]))
    assert p[0]["data"]["brightness_pct"] < 64
