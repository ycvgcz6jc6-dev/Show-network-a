import asyncio
from custom_components.dmx_monitor.power_manager import (
    ENABLED, PowerChannel, PowerOutput, PowerOutputConfig, PowerOutputPipeline,
    PowerSequence, build_artnet_frame, build_sacn_frame, build_enttec_frame,
)

def test_power_manager_is_explicit_active_subsystem():
    assert ENABLED is True
    assert {x.value for x in PowerOutput} == {"sacn", "artnet", "enttec"}

def test_sacn_allows_standard_multicast_but_artnet_requires_host():
    assert PowerOutputConfig(PowerOutput.SACN, universe=10).host == ""
    try: PowerOutputConfig(PowerOutput.ARTNET)
    except ValueError: pass
    else: raise AssertionError("Art-Net output must require a destination")

def test_enttec_requires_device():
    try: PowerOutputConfig(PowerOutput.ENTTEC)
    except ValueError: pass
    else: raise AssertionError("ENTTEC output must require a device")

def test_sequence_is_active_only_when_enabled():
    output=PowerOutputConfig(PowerOutput.ARTNET,universe=10,host="192.0.2.10")
    seq=PowerSequence(universe=10,output=output,channels=(PowerChannel(1,"Audio A",on_delay_s=2.0),),enabled=True)
    assert seq.active is True

def test_frames_have_expected_protocol_headers_and_512_slots():
    values=bytes(range(256))*2
    sacn=build_sacn_frame(10,values,sequence=7)
    assert sacn[:2] == b"\x00\x10" and b"ASC-E1.17" in sacn and sacn[113:115] == b"\x00\x0a"
    assert sacn[-512:] == values
    art=build_artnet_frame(10,values,sequence=7)
    assert art.startswith(b"Art-Net\x00\x00P") and art[-512:] == values
    ent=build_enttec_frame(values)
    assert ent[0] == 0x7E and ent[1] == 6 and ent[-1] == 0xE7 and len(ent) == 518

def test_output_pipeline_coalesces_latest_value():
    sent=[]
    async def run():
        gate=asyncio.Event()
        async def sender(frame): sent.append(frame); await gate.wait()
        p=PowerOutputPipeline(sender,interval_s=.02)
        p.push_nowait(bytes([1])*512); await asyncio.sleep(.01)
        p.push_nowait(bytes([2])*512);p.push_nowait(bytes([3])*512)
        gate.set();await asyncio.sleep(.05);await p.async_stop();return p.snapshot()
    stats=asyncio.run(run())
    assert sent[0][0]==1 and sent[-1][0]==3 and stats["coalesced"]>=1
