from custom_components.dmx_monitor.pre_show import PreShowCheck

def test_profile_is_optional_and_never_blocking(tmp_path):
    p=PreShowCheck(str(tmp_path))
    out=p.run({})
    assert out['profile_enabled'] is False
    assert out['blocking'] is False
    p.configure(enabled=True,name='Test',expected_dmx_universes=[1],require_timecode=True)
    out=p.run({'dmx_universes':[],'timecode':{'status':'unknown'}})
    assert out['state']=='NOT_READY'
    assert out['blocking'] is False
    p.disable()
    assert p.run({})['profile_enabled'] is False
