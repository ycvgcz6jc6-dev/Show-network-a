import asyncio
from pathlib import Path
from custom_components.dmx_monitor.core.state_store import RuntimeStateStore
from custom_components.dmx_monitor.core.observability import RuntimeMetrics
from custom_components.dmx_monitor.flow_pipeline import LatestValuePipeline
from custom_components.dmx_monitor.security import SecurityManager


def test_state_store_is_bounded():
    s = RuntimeStateStore(max_keys=3)
    s.update(a=1, b=2, c=3)
    s.update(d=4)
    assert len(s.snapshot()) <= 3
    assert s.get("d") == 4


def test_runtime_metrics_snapshot():
    m = RuntimeMetrics()
    m.record(received=10, processed=8, dropped=2)
    snap = m.snapshot()
    assert snap["received"] == 10
    assert snap["processed"] == 8
    assert snap["dropped"] == 2
    assert snap["uptime_s"] >= 0


def test_flow_pipeline_bounds_completed_keys():
    async def run():
        out = []
        async def processor(k, v):
            out.append((k, v))
        p = LatestValuePipeline(processor, interval_s=0.01, max_keys=2)
        for i in range(6):
            p.push_nowait(i, bytes([i]))
            await asyncio.sleep(0.015)
        await asyncio.sleep(0.03)
        assert len(p._last) <= 2
        await p.async_stop()
    asyncio.run(run())


def test_security_malformed_store_does_not_crash(tmp_path: Path):
    path = tmp_path / "show_network_security.json"
    path.write_text('{"salt":"not-hex","digest":"x"}', encoding='utf-8')
    s = SecurityManager(str(tmp_path))
    assert not s.verify("anything")


def test_security_bruteforce_lockout(tmp_path: Path):
    s = SecurityManager(str(tmp_path))
    s.set_password("correct-horse")
    for _ in range(5):
        assert not s.verify("wrong-password")
    assert not s.verify("correct-horse")


def test_latest_pipeline_coalesces_without_task_per_packet():
    async def run():
        out = []
        async def processor(k, v):
            await asyncio.sleep(0)
            out.append(v)
        p = LatestValuePipeline(processor, interval_s=0.02, max_keys=1)
        for i in range(1000):
            p.push_nowait("u1", bytes([i % 256]))
        await asyncio.sleep(0.05)
        assert p.stats.max_pending <= 1
        assert p.stats.coalesced > 0
        assert p.stats.worker_runs <= 2
        await p.async_stop()
    asyncio.run(run())
