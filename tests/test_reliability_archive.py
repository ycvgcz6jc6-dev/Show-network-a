from pathlib import Path
from custom_components.dmx_monitor.archive import EventArchive
from custom_components.dmx_monitor.reliability import capacity_snapshot

def test_archive_destination_and_timeline(tmp_path: Path):
    a=EventArchive(str(tmp_path), destination=str(tmp_path/'nas_mount'), retention_days=30)
    a.record('dmx','universe_change',{'universe':1})
    assert (tmp_path/'nas_mount'/'show_timeline.jsonl').exists()
    out=a.export_zip()
    assert out.exists()

def test_capacity_predictor():
    s=capacity_snapshot([{'protocol':'sACN','packet_rate':44},{'protocol':'Art-Net','packet_rate':44}], dante_mbps=100, cameras_mbps=300, link_mbps=1000)
    assert s['total_mbps'] > 400
    assert s['status']=='ok'
    assert s['utilization_pct'] < 75
