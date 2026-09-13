"""Generic DMX fixture catalogue loaded from validated YAML data."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .core.profile_loader import load_yaml_catalog, require_mapping, require_keys

@dataclass(frozen=True)
class ChannelCapability:
    attribute: str
    dmx_min: int = 0
    dmx_max: int = 255
    value_min: float = 0.0
    value_max: float = 1.0
    discrete: bool = False
@dataclass(frozen=True)
class FixtureChannel:
    name: str
    offset: int
    capability: ChannelCapability
@dataclass(frozen=True)
class FixtureMode:
    name: str
    channels: tuple[str, ...]
@dataclass(frozen=True)
class FixtureProfile:
    profile_id: str
    manufacturer: str
    model: str
    channels: tuple[FixtureChannel, ...]
    modes: tuple[FixtureMode, ...]
    def snapshot(self) -> dict[str, Any]: return asdict(self)

def _validate(data):
    data=require_mapping(data, name="fixtures")
    for key,item in data.items():
        item=require_mapping(item,name=f"fixtures.{key}")
        require_keys(item,{"profile_id","manufacturer","model","channels","modes"},name=f"fixtures.{key}")
        if item["profile_id"] != key: raise ValueError(f"fixtures.{key}.profile_id must match its key")
        if not isinstance(item["channels"],list) or not isinstance(item["modes"],list): raise ValueError(f"fixtures.{key}.channels/modes must be lists")
        for i,ch in enumerate(item["channels"]):
            require_mapping(ch,name=f"fixtures.{key}.channels[{i}]"); require_keys(ch,{"name","offset","capability"},name=f"fixtures.{key}.channels[{i}]")
            require_mapping(ch["capability"],name=f"fixtures.{key}.channels[{i}].capability"); require_keys(ch["capability"],{"attribute"},name=f"fixtures.{key}.channels[{i}].capability")
        for i,mode in enumerate(item["modes"]):
            require_mapping(mode,name=f"fixtures.{key}.modes[{i}]"); require_keys(mode,{"name","channels"},name=f"fixtures.{key}.modes[{i}]")

_RAW=load_yaml_catalog("fixtures.yaml",_validate)
PROFILES={}
for key,item in _RAW.items():
    channels=tuple(FixtureChannel(c["name"],int(c["offset"]),ChannelCapability(**c["capability"])) for c in item["channels"])
    modes=tuple(FixtureMode(m["name"],tuple(m["channels"])) for m in item["modes"])
    PROFILES[key]=FixtureProfile(item["profile_id"],item["manufacturer"],item["model"],channels,modes)
def get(profile_id: str | None) -> FixtureProfile | None: return PROFILES.get(str(profile_id or ""))
def snapshot() -> list[dict[str,Any]]: return [p.snapshot() for p in PROFILES.values()]
