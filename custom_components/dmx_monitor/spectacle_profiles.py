"""Conservative show/audio manufacturer catalogue loaded from YAML."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys

@dataclass(frozen=True)
class ShowManufacturerProfile:
    key: str
    manufacturer: str
    domains: tuple[str, ...]
    product_families: tuple[str, ...]
    passive_protocols: tuple[str, ...]
    diagnostics: tuple[str, ...]
    control_paths: tuple[str, ...] = ()

def _validate(data):
    for i,item in enumerate(require_list(data,name="spectacle_profiles")):
        item=require_mapping(item,name=f"spectacle_profiles[{i}]")
        require_keys(item,{"key","manufacturer","domains","product_families","passive_protocols","diagnostics"},name=f"spectacle_profiles[{i}]")
        for field in ("domains","product_families","passive_protocols","diagnostics","control_paths"):
            if field in item and not isinstance(item[field],list): raise ValueError(f"spectacle_profiles[{i}].{field} must be a list")
_RAW=load_yaml_catalog("spectacle_profiles.yaml",_validate)
PROFILES=tuple(ShowManufacturerProfile(x["key"],x["manufacturer"],tuple(x["domains"]),tuple(x["product_families"]),tuple(x["passive_protocols"]),tuple(x["diagnostics"]),tuple(x.get("control_paths",()))) for x in _RAW)
def get_profile(key: str): return next((p for p in PROFILES if p.key==key),None)
def snapshot(): return [asdict(p) for p in PROFILES]
