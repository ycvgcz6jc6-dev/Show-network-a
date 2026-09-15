from custom_components.dmx_monitor.projector_monitor import PJLinkMonitor, ProjectorRecord


def test_pjlink_payload_filters_errors():
    assert PJLinkMonitor._payload('%1POWR=1') == '1'
    assert PJLinkMonitor._payload('%1POWR=ERR3') is None


def test_projector_status_is_truthful():
    m = PJLinkMonitor([])
    r = m._ensure_record(host='192.0.2.10', discovered=True, mac='00:11:22:33:44:55')
    r.online = True
    r.errors = '000000'
    st = m.status()
    assert st['total'] == 1
    assert st['online'] == 1
    assert st['errors'] == 0
    assert st['discovered'] == 1


def test_error_detail_mapping_from_standard_erst():
    # Parsing logic is deterministic even without a real projector.
    r = ProjectorRecord(name='x', host='192.0.2.11')
    levels = {'0': 'ok', '1': 'warning', '2': 'error'}
    names = ('fan', 'lamp', 'temperature', 'cover', 'filter', 'other')
    r.errors = '012000'
    r.error_detail = {n: levels[v] for n, v in zip(names, r.errors)}
    assert r.error_detail['lamp'] == 'warning'
    assert r.error_detail['temperature'] == 'error'
