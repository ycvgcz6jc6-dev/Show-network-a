from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CC=ROOT/'custom_components'/'dmx_monitor'

def test_version_0135():
    assert '"version": "0.15.2"' in (CC/'manifest.json').read_text()
    assert 'VERSION = "0.15.2"' in (CC/'const.py').read_text()
    assert 'show-network.js?v=0.15.2' in (CC/'__init__.py').read_text()

def test_dmx_publish_limiter_uses_real_pending_token():
    text=(CC/'coordinator.py').read_text()
    assert 'push_nowait(key, self._publish_dmx_snapshot)' in text
    assert 'push_nowait(None, self._publish_dmx_snapshot)' not in text

def test_frontend_cockpit_and_local_module_gates():
    js=(CC/'static'/'show-network.js').read_text()
    for marker in ('DMX NETWORK','DMX IN / ENTTEC','MA-NET3','DANTE / PTP','PROFILS / CONSTRUCTEURS'):
        assert marker in js
    assert '_moduleGate(module,label,key)' in js
    assert 'L’activation se fait maintenant dans la page du module concerné.' in js
    assert 'Aucun projecteur PJLink observé.' in js

def test_rule_builder_supports_values_b64_and_punchlight_feedback():
    js=(CC/'static'/'show-network.js').read_text()
    assert 'if(x.values_b64)' in js
    assert "b.textContent='Recherche…'" in js
