from custom_components.dmx_monitor.show_snapshot import ShowSnapshotManager

def test_show_snapshot_compare(tmp_path):
    m=ShowSnapshotManager(str(tmp_path)); data={"device_model":{"devices":[{"id":"ip:1","name":"MA3","ip":"10.0.0.1","protocols":["sacn"]}]},"dmx_universe_matrix":[{"protocol":"sacn","universe":1,"sources":[{"active":True,"source":"10.0.0.1","cid":"abc","priority":100}]}]}
    m.create("Show A",data); assert m.compare(data)["state"]=="match"
    changed={"device_model":{"devices":[]},"dmx_universe_matrix":[]}; r=m.compare(changed); assert r["state"]=="warning"; assert r["warning_count"]==2


def test_constructor_does_not_block_event_loop_by_auto_loading(tmp_path):
    """Regression test for a real production finding: __init__ used to
    call self._load() synchronously, and since ShowSnapshotManager is
    constructed directly inside ShowNetworkCoordinator.__init__ (itself
    on the event loop), this blocked it on every single startup --
    confirmed via Home Assistant's own "Detected blocking call to open"
    warning after deploying this project's own fix for the same class
    of bug on two *other* managers, which had simply missed this one.
    Loading is now deferred to runtime/setup.py's _safe_load list,
    calling manager._load directly (the same pattern already used for
    pre_show._load/incident_center._load)."""
    import json
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir()
    path = storage_dir / "show_network_show_snapshots.json"
    path.write_text(json.dumps({"active": "x", "snapshots": {"x": {"devices": []}}}), encoding="utf-8")

    manager = ShowSnapshotManager(str(tmp_path))
    # The constructor must NOT have read the file -- data stays at the
    # untouched default until _load() is explicitly called.
    assert manager._data == {"active": None, "snapshots": {}}

    manager._load()
    assert manager._data["active"] == "x"
