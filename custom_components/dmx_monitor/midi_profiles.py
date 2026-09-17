"""MIDI source catalogue loaded from validated YAML data."""
from __future__ import annotations
from dataclasses import dataclass
from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys, LazyCatalog
@dataclass(frozen=True)
class MIDIProfile:
    key:str; label_fr:str; label_en:str; description_fr:str; description_en:str
def _validate(data):
    for i,x in enumerate(require_list(data,name="midi_profiles")):
        x=require_mapping(x,name=f"midi_profiles[{i}]"); require_keys(x,{"key","label_fr","label_en","description_fr","description_en"},name=f"midi_profiles[{i}]")
def _load() -> tuple[MIDIProfile, ...]:
    return tuple(MIDIProfile(**x) for x in load_yaml_catalog("midi_profiles.yaml",_validate))
# NOTE (audit fix): was eager at import time. See osc_profiles.py's
# PROFILES for the full explanation.
PROFILES = LazyCatalog(_load)
