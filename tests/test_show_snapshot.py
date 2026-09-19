from custom_components.dmx_monitor.show_snapshot import ShowSnapshotManager

def test_show_snapshot_compare(tmp_path):
    m=ShowSnapshotManager(str(tmp_path)); data={"device_model":{"devices":[{"id":"ip:1","name":"MA3","ip":"10.0.0.1","protocols":["sacn"]}]},"dmx_universe_matrix":[{"protocol":"sacn","universe":1,"sources":[{"active":True,"source":"10.0.0.1","cid":"abc","priority":100}]}]}
    m.create("Show A",data); assert m.compare(data)["state"]=="match"
    changed={"device_model":{"devices":[]},"dmx_universe_matrix":[]}; r=m.compare(changed); assert r["state"]=="warning"; assert r["warning_count"]==2
