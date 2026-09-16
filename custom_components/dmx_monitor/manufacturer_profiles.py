"""Unified descriptive manufacturer catalogue; no vendor probing or control."""
from __future__ import annotations
from dataclasses import asdict
from .core.profile_loader import load_yaml_catalog, require_mapping
from .spectacle_profiles import PROFILES, get_profile
from .switch_profiles import SWITCH_PROFILES

_ALIASES=load_yaml_catalog("manufacturers.yaml",lambda x: require_mapping(x,name="manufacturers"))

def all_profiles() -> list[dict]:
    return [{**asdict(p), "profile_type":"show"} for p in PROFILES] + [{**asdict(p), "profile_type":"switch"} for p in SWITCH_PROFILES]

def match_manufacturer(text: str) -> dict | None:
    t=(text or "").lower()
    for alias,key in _ALIASES.items():
        if alias in t:
            p=get_profile(key)
            if p:
                d=asdict(p); d["confidence"]="candidate"; d["evidence"]=[f"manufacturer marker observed: {alias}"]; return d
    return None
