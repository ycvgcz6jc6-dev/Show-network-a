"""Validated YAML catalogue loading for Show Network.

Profile data is deliberately kept outside Python code.  Loaders validate the
shape and reject malformed catalogue entries early, while runtime code keeps
using typed dataclasses for compatibility and predictable behaviour.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import yaml


class ProfileDataError(ValueError):
    """Raised when a static profile catalogue is malformed."""


class LazyCatalog:
    """Sequence/mapping-like proxy that defers ``loader()`` until first real
    access, or until ``warm()`` is called explicitly (e.g. from an executor
    job during async Home Assistant setup).

    fixture_profiles.py already hand-rolled this exact pattern (its
    ``_LazyProfiles`` dict subclass) to avoid the blocking synchronous YAML
    read that ``load_yaml_catalog`` performs happening on Home Assistant's
    event loop at module-import time -- an audited, confirmed-in-production
    issue (5 blocking-I/O warnings logged at startup). This is the same
    idea generalized so every other catalogue module (osc_profiles.py,
    switch_profiles.py, spectacle_profiles.py, manufacturer_profiles.py,
    midi_profiles.py) can use it too, for both tuple- and dict-shaped
    catalogues, without duplicating the proxy machinery in each file.

    If nothing ever calls ``warm()`` from an executor, correctness is not
    affected -- the first real access still triggers the load, just
    synchronously and possibly on the event loop, exactly like before this
    fix existed. ``warm()`` is what actually moves the I/O off the loop.
    """

    def __init__(self, loader: Callable[[], Any]) -> None:
        self._loader = loader
        self._value: Any = None
        self._loaded = False

    def warm(self) -> Any:
        """Force the load now. Call this from hass.async_add_executor_job."""
        if not self._loaded:
            self._value = self._loader()
            self._loaded = True
        return self._value

    def _ensure(self) -> Any:
        return self._value if self._loaded else self.warm()

    def __iter__(self):
        return iter(self._ensure())

    def __len__(self):
        return len(self._ensure())

    def __getitem__(self, key):
        return self._ensure()[key]

    def __contains__(self, item):
        return item in self._ensure()

    def __bool__(self):
        return bool(self._ensure())

    def get(self, key, default=None):
        value = self._ensure()
        return value.get(key, default) if hasattr(value, "get") else default

    def items(self):
        return self._ensure().items()

    def values(self):
        return self._ensure().values()

    def keys(self):
        return self._ensure().keys()

    def __repr__(self):
        return f"LazyCatalog(loaded={self._loaded}, value={self._value!r})"


def warm_catalogs(*catalogs: Any) -> None:
    """Warm lazy catalogues while tolerating already-materialized values.

    Older Show Network releases exported some catalogues directly as tuples
    or dictionaries.  Accepting those values here makes upgrades safe when
    Home Assistant still has an older module object in memory, while lazy
    catalogues continue to perform their disk reads in the executor selected
    by the caller.
    """
    for catalog in catalogs:
        warm = getattr(catalog, "warm", None)
        if callable(warm):
            warm()


def load_yaml_catalog(filename: str, validator: Callable[[Any], None]) -> Any:
    path = Path(__file__).resolve().parent.parent / "data" / filename
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except OSError as err:
        raise ProfileDataError(f"Unable to read profile catalogue {filename}: {err}") from err
    except yaml.YAMLError as err:
        raise ProfileDataError(f"Invalid YAML in profile catalogue {filename}: {err}") from err
    validator(data)
    return data


def require_list(value: Any, *, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProfileDataError(f"{name} must be a YAML list")
    return value


def require_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileDataError(f"{name} must be a YAML mapping")
    if not all(isinstance(key, str) for key in value):
        raise ProfileDataError(f"{name} keys must be strings")
    return value


def require_keys(value: dict[str, Any], keys: set[str], *, name: str) -> None:
    missing = keys - value.keys()
    if missing:
        raise ProfileDataError(f"{name} missing required keys: {', '.join(sorted(missing))}")
