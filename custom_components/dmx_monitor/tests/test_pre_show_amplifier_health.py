from custom_components.dmx_monitor.pre_show import PreShowCheck


def _base(amps):
    return {"audio_amplifiers": amps, "dmx_universes": [], "switch_telemetry": [], "projectors": []}


def _amp_check(result):
    return next(x for x in result["checks"] if x["id"] == "amps")


def test_offline_amplifier_is_fail():
    r=PreShowCheck().run(_base([{"key":"amp1","host":"10.0.0.5","online":False,"error":None}]))
    assert _amp_check(r)["status"] == "fail"
    assert _amp_check(r)["evidence"]["faults"][0]["host"] == "10.0.0.5"


def test_explicit_amplifier_error_is_fail():
    r=PreShowCheck().run(_base([{"key":"amp1","online":True,"error":"fault"}]))
    assert _amp_check(r)["status"] == "fail"


def test_online_amplifier_without_error_is_pass():
    r=PreShowCheck().run(_base([{"key":"amp1","online":True,"error":None}]))
    assert _amp_check(r)["status"] == "pass"
