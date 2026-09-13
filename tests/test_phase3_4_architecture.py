from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'custom_components' / 'dmx_monitor'

def test_protocol_catalog_covers_runtime_adapters():
    text = (PKG / 'protocols' / 'catalog.py').read_text()
    expected = {'dmx-network','enttec','ma-net3','osc','midi','dante','aes67','ptp','st2110','avb','punchlight'}
    assert all(f'"{key}"' in text for key in expected)
    assert 'receive_only: bool = True' in text

def test_runtime_setup_uses_catalogue_boundary():
    text = (PKG / 'runtime' / 'setup.py').read_text()
    assert 'get_adapter_spec' in text
    assert '_adapter("dante")' in text
    assert '_adapter("dmx-network")' in text
    assert '_adapter("midi")' in text

def test_coordinator_has_no_direct_ha_action_queue():
    text = (PKG / 'coordinator.py').read_text()
    assert '_ha_action_queue' not in text
    assert '_ha_action_loop' not in text
    assert 'HAActionDispatcher' in text

def test_blocking_discovery_runs_off_event_loop():
    for name in ('vendor_discovery.py','punchlight_network.py','midi_runtime.py'):
        text = (PKG / name).read_text()
        assert 'asyncio.to_thread' in text

def test_projector_and_snmp_blocking_calls_are_worker_bound():
    for name in ('projector_monitor.py','snmp.py'):
        tree = ast.parse((PKG / name).read_text())
        text = (PKG / name).read_text()
        if name == 'projector_monitor.py':
            assert 'run_in_executor' in text
        else:
            assert 'recvfrom' in text

def test_state_contracts_are_ha_independent():
    contracts = (PKG / 'core' / 'contracts.py').read_text()
    store = (PKG / 'core' / 'state_store.py').read_text()
    assert 'class ProtocolObservation' in contracts
    assert 'class ServiceAction' in contracts
    assert 'homeassistant' not in contracts.lower()
    assert 'class RuntimeStateStore' in store
    assert 'homeassistant' not in store.lower()
