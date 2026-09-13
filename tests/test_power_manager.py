from custom_components.dmx_monitor.power_manager import (
    ENABLED,
    PowerChannel,
    PowerOutput,
    PowerOutputConfig,
    PowerSequence,
    available_outputs,
)


def test_power_manager_is_dormant_and_separate():
    assert ENABLED is False
    assert available_outputs() == (PowerOutput.SACN, PowerOutput.ARTNET, PowerOutput.ENTTEC)


def test_network_output_requires_host():
    try:
        PowerOutputConfig(PowerOutput.SACN)
    except ValueError:
        pass
    else:
        raise AssertionError("network output must require a host")


def test_enttec_output_requires_device():
    try:
        PowerOutputConfig(PowerOutput.ENTTEC)
    except ValueError:
        pass
    else:
        raise AssertionError("ENTTEC output must require a device")


def test_sequence_can_declare_output_without_sending_anything():
    output = PowerOutputConfig(PowerOutput.ARTNET, universe=10, host="192.0.2.10")
    seq = PowerSequence(
        universe=10,
        output=output,
        channels=(PowerChannel(1, "Audio A", on_delay_s=2.0),),
        enabled=True,
    )
    assert seq.active is False
    assert seq.output.output is PowerOutput.ARTNET


def test_power_output_pipeline_is_bounded_and_latest_value():
    from custom_components.dmx_monitor.power_manager import PowerOutputPipeline
    async def run():
        sent = []
        def sender(frame):
            sent.append(frame)
        p = PowerOutputPipeline(sender, interval_s=0.02)
        for i in range(100):
            p.push_nowait(bytes([i]))
        await asyncio.sleep(0.06)
        assert p.received == 100
        assert p.coalesced > 0
        assert len(sent) < 100
        assert all(len(frame) == 512 for frame in sent)
        await p.async_stop()
    import asyncio
    asyncio.run(run())
