"""Independent catalogue tests; no Home Assistant runtime is required."""
from __future__ import annotations
import importlib.util
import sys
import types
from pathlib import Path

ROOT=Path(__file__).parents[1]

# Load the integration subpackage without executing Home Assistant's integration
# entry point, so catalogue validation can run in a minimal Python environment.
pkg=types.ModuleType("custom_components"); pkg.__path__=[str(ROOT/"custom_components")]; sys.modules.setdefault("custom_components",pkg)
sub=types.ModuleType("custom_components.dmx_monitor"); sub.__path__=[str(ROOT/"custom_components/dmx_monitor")]; sys.modules.setdefault("custom_components.dmx_monitor",sub)

def test_catalogues_load_and_have_unique_keys():
    from custom_components.dmx_monitor.switch_profiles import SWITCH_PROFILES
    from custom_components.dmx_monitor.fixture_profiles import PROFILES as fixtures
    from custom_components.dmx_monitor.spectacle_profiles import PROFILES as spectacle
    from custom_components.dmx_monitor.osc_profiles import PROFILES as osc
    from custom_components.dmx_monitor.midi_profiles import PROFILES as midi
    assert len({p.key for p in SWITCH_PROFILES}) == len(SWITCH_PROFILES)
    assert len(fixtures) >= 1
    assert len({p.key for p in spectacle}) == len(spectacle)
    assert len({p.key for p in osc}) == len(osc)
    assert len({p.key for p in midi}) == len(midi)

def test_default_switch_catalogue_is_stable():
    from custom_components.dmx_monitor.switch_profiles import enabled_profiles
    assert [p.key for p in enabled_profiles()] == ["luminex", "elc", "green_go"]

def test_fixture_schema_is_typed():
    from custom_components.dmx_monitor.fixture_profiles import get
    p=get("generic.rgbw.4ch")
    assert p is not None
    assert len(p.channels) == 4
    assert p.channels[-1].capability.attribute == "white"
