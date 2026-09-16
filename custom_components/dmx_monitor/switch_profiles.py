"""Managed-switch SNMP capability catalogue.

Loads the already-present ``data/switches.yaml`` catalogue: one entry per
switch vendor with which SNMP transport it uses, the standard MIB-II /
LLDP-MIB fields it exposes, and the vendor-specific features (temperature,
PoE, SFP optics, CPU/memory, VLAN, IGMP, PTP, port bandwidth...) that are
documented as available. This module never queries a device itself -- it
only describes what GigaCoreMonitor and any future vendor-specific SNMP
client are allowed to ask for. Actually walking LLDP-MIB (lldpRemTable) is
not implemented anywhere yet: it is listed here as a documented capability
so the UI/catalog can say a vendor supports it, but no code currently polls
it (see the network topology module for that gap).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys

_REQUIRED_KEYS = {
    "key",
    "manufacturer",
    "display_name",
    "enabled_by_default",
    "transport",
    "standard_features",
    "vendor_features",
}

_LIST_FIELDS = ("transport", "standard_features", "vendor_features")


def _validate(data) -> None:
    for i, item in enumerate(require_list(data, name="switches")):
        item = require_mapping(item, name=f"switches[{i}]")
        require_keys(item, _REQUIRED_KEYS, name=f"switches[{i}]")
        for field_name in _LIST_FIELDS:
            if not isinstance(item[field_name], list):
                raise ValueError(f"switches[{i}].{field_name} must be a list")
        if not isinstance(item["enabled_by_default"], bool):
            raise ValueError(f"switches[{i}].enabled_by_default must be a bool")


@dataclass(frozen=True)
class SwitchProfile:
    key: str
    manufacturer: str
    display_name: str
    enabled_by_default: bool
    transport: tuple[str, ...] = field(default_factory=tuple)
    standard_features: tuple[str, ...] = field(default_factory=tuple)
    vendor_features: tuple[str, ...] = field(default_factory=tuple)


_RAW = load_yaml_catalog("switches.yaml", _validate)

SWITCH_PROFILES: tuple[SwitchProfile, ...] = tuple(
    SwitchProfile(
        key=x["key"],
        manufacturer=x["manufacturer"],
        display_name=x["display_name"],
        enabled_by_default=bool(x["enabled_by_default"]),
        transport=tuple(x["transport"]),
        standard_features=tuple(x["standard_features"]),
        vendor_features=tuple(x["vendor_features"]),
    )
    for x in _RAW
)

_BY_KEY: dict[str, SwitchProfile] = {p.key: p for p in SWITCH_PROFILES}


def get_profile(key: str) -> SwitchProfile | None:
    return _BY_KEY.get(key)


def enabled_profiles(selected: Iterable[str] | None = None) -> list[SwitchProfile]:
    """Return the switch profiles that should currently be polled.

    - If ``selected`` is None/empty (nothing explicitly configured yet, e.g.
      right after first setup): fall back to every profile whose
      ``enabled_by_default`` is True (matches data/switches.yaml: Luminex,
      ELC, Green-GO today).
    - If ``selected`` is a non-empty iterable of manufacturer keys (from the
      config entry's ``switch_manufacturers`` option): honor that selection
      exactly, regardless of each profile's own default flag, so a user who
      explicitly turns on Cisco/Aruba/etc. gets it, and one who turns off a
      default-enabled vendor no longer polls it. Unknown keys are ignored
      rather than raising, consistent with this codebase's general
      never-crash-on-a-stale-config-value style.
    """
    if not selected:
        return [p for p in SWITCH_PROFILES if p.enabled_by_default]
    wanted = {str(k) for k in selected}
    return [p for p in SWITCH_PROFILES if p.key in wanted]


def all_keys() -> tuple[str, ...]:
    return tuple(_BY_KEY.keys())
