"""Predefined OSC source catalogue loaded from YAML data."""
from __future__ import annotations
from dataclasses import dataclass, field
from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys

@dataclass(frozen=True)
class OSCActionTemplate:
    key: str; label_fr: str; label_en: str; address: str; value_type: str
    destination_domain: str; destination_attribute: str; notes_fr: str = ""; notes_en: str = ""
@dataclass(frozen=True)
class OSCSourceProfile:
    key: str; label_fr: str; label_en: str; description_fr: str; description_en: str
    setup_steps_fr: tuple[str,...]; setup_steps_en: tuple[str,...]; actions: tuple[OSCActionTemplate,...]=field(default_factory=tuple)

def _validate(data):
    for i,item in enumerate(require_list(data,name="osc_profiles")):
        item=require_mapping(item,name=f"osc_profiles[{i}]")
        require_keys(item,{"key","label_fr","label_en","description_fr","description_en","setup_steps_fr","setup_steps_en","actions"},name=f"osc_profiles[{i}]")
        for field in ("setup_steps_fr","setup_steps_en","actions"):
            if not isinstance(item[field],list): raise ValueError(f"osc_profiles[{i}].{field} must be a list")
        for j,a in enumerate(item["actions"]):
            a=require_mapping(a,name=f"osc_profiles[{i}].actions[{j}]")
            require_keys(a,{"key","label_fr","label_en","address","value_type","destination_domain","destination_attribute"},name=f"osc_profiles[{i}].actions[{j}]")
_RAW=load_yaml_catalog("osc_profiles.yaml",_validate)
PROFILES=tuple(OSCSourceProfile(x["key"],x["label_fr"],x["label_en"],x["description_fr"],x["description_en"],tuple(x["setup_steps_fr"]),tuple(x["setup_steps_en"]),tuple(OSCActionTemplate(**a) for a in x.get("actions",()))) for x in _RAW)
