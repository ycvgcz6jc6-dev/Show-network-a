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

_LOADED = False

class _LazyProfiles(dict[str, FixtureProfile]):
    def _ensure(self):
        if not _LOADED:
            load_profiles()
    def __len__(self):
        self._ensure(); return dict.__len__(self)
    def __iter__(self):
        self._ensure(); return dict.__iter__(self)
    def get(self, key, default=None):
        self._ensure(); return dict.get(self, key, default)
    def values(self):
        self._ensure(); return dict.values(self)
    def items(self):
        self._ensure(); return dict.items(self)

PROFILES: dict[str, FixtureProfile] = _LazyProfiles()

def load_profiles() -> dict[str, FixtureProfile]:
    """Load the static fixture catalogue. Call from an executor in HA setup."""
    global _LOADED
    if _LOADED:
        return PROFILES
    raw = load_yaml_catalog("fixtures.yaml", _validate)
    built = {}
    for key,item in raw.items():
        channels=tuple(FixtureChannel(c["name"],int(c["offset"]),ChannelCapability(**c["capability"])) for c in item["channels"])
        modes=tuple(FixtureMode(m["name"],tuple(m["channels"])) for m in item["modes"])
        built[key]=FixtureProfile(item["profile_id"],item["manufacturer"],item["model"],channels,modes)
    dict.clear(PROFILES); dict.update(PROFILES, built); _LOADED = True
    return PROFILES

def get(profile_id: str | None) -> FixtureProfile | None:
    if not _LOADED:
        load_profiles()
    return PROFILES.get(str(profile_id or ""))

def snapshot() -> list[dict[str,Any]]:
    if not _LOADED:
        load_profiles()
    return [p.snapshot() for p in PROFILES.values()]
