"""Manufacturer capability catalogue for show/AV/network equipment.

Loads the already-present ``data/spectacle_profiles.yaml`` catalogue: one
entry per manufacturer with the domains it covers (AUDIO/LIGHTING/VIDEO/
NETWORK), documented product families, the *passive* protocols it can be
observed over, the diagnostics fields that are documented as available, and
the control paths that officially exist for it (metadata only -- this module
never talks to a device, it only describes what is publicly documented).

This is deliberately a read-only reference catalogue, in the same spirit as
``osc_profiles.py`` and ``switch_profiles.py``: the data lives in YAML, this
module only validates its shape and exposes it as typed, immutable objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys

_REQUIRED_KEYS = {
    "key",
    "manufacturer",
    "domains",
    "product_families",
    "passive_protocols",
    "diagnostics",
    "control_paths",
}

_LIST_FIELDS = ("domains", "product_families", "passive_protocols", "diagnostics", "control_paths")


def _validate(data) -> None:
    for i, item in enumerate(require_list(data, name="spectacle_profiles")):
        item = require_mapping(item, name=f"spectacle_profiles[{i}]")
        require_keys(item, _REQUIRED_KEYS, name=f"spectacle_profiles[{i}]")
        for field_name in _LIST_FIELDS:
            if not isinstance(item[field_name], list):
                raise ValueError(f"spectacle_profiles[{i}].{field_name} must be a list")


@dataclass(frozen=True)
class SpectacleManufacturerProfile:
    key: str
    manufacturer: str
    domains: tuple[str, ...] = field(default_factory=tuple)
    product_families: tuple[str, ...] = field(default_factory=tuple)
    passive_protocols: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
    control_paths: tuple[str, ...] = field(default_factory=tuple)


_RAW = load_yaml_catalog("spectacle_profiles.yaml", _validate)

PROFILES: tuple[SpectacleManufacturerProfile, ...] = tuple(
    SpectacleManufacturerProfile(
        key=x["key"],
        manufacturer=x["manufacturer"],
        domains=tuple(x["domains"]),
        product_families=tuple(x["product_families"]),
        passive_protocols=tuple(x["passive_protocols"]),
        diagnostics=tuple(x["diagnostics"]),
        control_paths=tuple(x["control_paths"]),
    )
    for x in _RAW
)

_BY_KEY: dict[str, SpectacleManufacturerProfile] = {p.key: p for p in PROFILES}


def get_profile(key: str) -> SpectacleManufacturerProfile | None:
    """Return the profile for ``key``, or None if unknown.

    Note: not every manufacturer alias in data/manufacturers.yaml has a
    matching entry here (e.g. netgear/ubiquiti/mikrotik/tp_link/
    allied_telesis/juniper only exist in data/switches.yaml today), so
    callers must handle a None result -- this mirrors how
    manufacturer_profiles.match_manufacturer() already treats a miss.
    """
    return _BY_KEY.get(key)


def all_keys() -> tuple[str, ...]:
    return tuple(_BY_KEY.keys())
