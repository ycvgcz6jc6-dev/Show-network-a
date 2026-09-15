"""Static architecture invariants for the modular runtime."""
from __future__ import annotations
import ast
import re
from pathlib import Path
import yaml

ROOT=Path(__file__).parents[1]
COMP=ROOT/"custom_components/dmx_monitor"

def test_entrypoint_is_thin():
    lines=(COMP/"__init__.py").read_text().splitlines()
    assert len(lines) < 180
    assert "async_setup_runtime" in "\n".join(lines)
    assert "async_register_services" in "\n".join(lines)

def test_service_registry_covers_yaml():
    service_names=set(yaml.safe_load((COMP/"services.yaml").read_text()))
    registered=set()
    for path in (COMP/"services").glob("*.py"):
        registered.update(re.findall(r'async_register\(DOMAIN,\s*["\']([^"\']+)',path.read_text()))
    assert service_names == registered
    assert len(registered) == 80

def test_runtime_resources_have_explicit_stop_methods():
    tree=ast.parse((COMP/"runtime/setup.py").read_text())
    source=(COMP/"runtime/setup.py").read_text()
    assert "RuntimeResource" in source
    assert "async_setup_runtime" in source
    assert tree is not None

def test_catalogues_are_data_files():
    data=COMP/"data"
    for name in ("switches.yaml","fixtures.yaml","spectacle_profiles.yaml","osc_profiles.yaml","midi_profiles.yaml"):
        assert (data/name).is_file()
