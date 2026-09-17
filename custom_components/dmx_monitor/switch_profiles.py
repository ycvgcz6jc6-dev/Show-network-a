"""Generic switch catalogue loaded from validated YAML data."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .core.profile_loader import load_yaml_catalog, require_list, require_mapping, require_keys, LazyCatalog

@dataclass(frozen=True)
class SwitchProfile:
    key: str
    manufacturer: str
    display_name: str
    enabled_by_default: bool = False
    transport: tuple[str, ...] = ("snmp_v2c",)
    standard_features: tuple[str, ...] = ("sysName", "sysDescr", "sysUpTime", "ifTable", "ifXTable", "lldpRemTable")
    vendor_features: tuple[str, ...] = ()


def _validate(data):
    for i, item in enumerate(require_list(data, name="switches")):
        item = require_mapping(item, name=f"switches[{i}]")
        require_keys(item, {"key", "manufacturer", "display_name"}, name=f"switches[{i}]")
        if not isinstance(item["key"], str) or not item["key"]:
            raise ValueError(f"switches[{i}].key must be non-empty")
        for field in ("transport", "standard_features", "vendor_features"):
            if field in item and not isinstance(item[field], list):
                raise ValueError(f"switches[{i}].{field} must be a list")

def _load() -> tuple[SwitchProfile, ...]:
    raw = load_yaml_catalog("switches.yaml", _validate)
    return tuple(SwitchProfile(
        key=x["key"], manufacturer=x["manufacturer"], display_name=x["display_name"],
        enabled_by_default=bool(x.get("enabled_by_default", False)),
        transport=tuple(x.get("transport", ("snmp_v2c",))),
        standard_features=tuple(x.get("standard_features", ("sysName", "sysDescr", "sysUpTime", "ifTable", "ifXTable", "lldpRemTable"))),
        vendor_features=tuple(x.get("vendor_features", ())),
    ) for x in raw)

# NOTE (audit fix): was eager at import time (blocking synchronous YAML
# read on the event loop, confirmed at Home Assistant startup). See
# osc_profiles.py's PROFILES for the full explanation of this pattern.
SWITCH_PROFILES = LazyCatalog(_load)

def profiles() -> list[dict]: return [asdict(item) for item in SWITCH_PROFILES]
def enabled_profiles(selected: list[str] | tuple[str, ...] | None = None) -> list[SwitchProfile]:
    """Return the switch profiles enabled for the given manufacturer keys.

    ``selected`` is the raw list of manufacturer keys (e.g. coordinator.data
    ["switch_manufacturers"]), not a settings dict — the previous signature
    expected a dict and called .get("switch_manufacturers") on it, which
    crashed with AttributeError as soon as a list was passed in (the only
    real caller, ShowNetworkCoordinator, always passes a list).
    """
    if selected is None: return [p for p in SWITCH_PROFILES if p.enabled_by_default]
    selected = set(selected)
    return [p for p in SWITCH_PROFILES if p.key in selected]
