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
