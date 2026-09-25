"""Small HA Builder for virtual Show Network entities.

Creates native Home Assistant entities owned by Show Network. It does not
pretend to install third-party integrations; it prepares stable, typed HA
entities with proper metadata and persists their definitions.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ALLOWED_TYPES = {"switch", "sensor", "binary_sensor", "button", "number"}

@dataclass
class HABuilderItem:
    item_id: str
    name: str
    entity_type: str = "switch"
    device_class: str | None = None
    unit: str | None = None
    icon: str | None = None
    area: str | None = None
    enabled: bool = True
    state: Any = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

class HABuilder:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.items: dict[str, HABuilderItem] = {}
        self.load()

    def load(self) -> list[HABuilderItem]:
        try:
            rows = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        self.items = {}
        for row in rows if isinstance(rows, list) else []:
            try:
                item = HABuilderItem(**row)
                if item.entity_type in ALLOWED_TYPES:
                    self.items[item.item_id] = item
            except (TypeError, ValueError):
                continue
        return list(self.items.values())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(x) for x in self.items.values()], ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def slug(value: str) -> str:
        out = "".join(c.lower() if c.isalnum() else "_" for c in str(value))
        return "_".join(x for x in out.split("_") if x)[:64] or "item"

    def create(self, name: str, entity_type: str = "switch", item_id: str | None = None, **kwargs) -> HABuilderItem:
        entity_type = str(entity_type).lower()
        if entity_type not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported HA Builder type: {entity_type}")
        item_id = self.slug(item_id or name)
        item = HABuilderItem(item_id=item_id, name=str(name)[:120], entity_type=entity_type,
                             device_class=kwargs.get("device_class"), unit=kwargs.get("unit"),
                             icon=kwargs.get("icon"), area=kwargs.get("area"),
                             enabled=bool(kwargs.get("enabled", True)), state=None,
                             min_value=kwargs.get("min_value"), max_value=kwargs.get("max_value"), step=kwargs.get("step"))
        initial_state = kwargs.get("state")
        # Only coerce/validate a state the caller actually supplied; leave
        # the default None alone so creating an item with no initial value
        # keeps working (a number item has no min/max-checkable value yet).
        item.state = self._coerce_state(item, initial_state) if initial_state is not None else None
        self.items[item_id] = item
        self.save()
        return item

    def remove(self, item_id: str) -> None:
        self.items.pop(str(item_id), None)
        self.save()

    def set_state(self, item_id: str, state: Any) -> None:
        if item_id not in self.items:
            raise ValueError(f"Unknown HA Builder item: {item_id}")
        item = self.items[item_id]
        self.items[item_id].state = self._coerce_state(item, state)
        self.save()

    @staticmethod
    def _coerce_state(item: "HABuilderItem", state: Any) -> Any:
        """Normalize an incoming state to match the item's declared entity_type.

        HA Builder items are written from several places (the
        ha_builder_set_state service, and the native switch/binary_sensor
        async_turn_on/off and number async_set_native_value entity methods),
        and all of them must agree on what a value means.

        Two audit-confirmed bugs came from skipping this step:
        - switch/binary_sensor: Python's bare bool("false") is True (any
          non-empty string is truthy), so writing the text "false" silently
          turned the entity on. Recognized textual tokens are mapped
          explicitly instead of relying on Python truthiness.
        - number: writes made through the ha_builder_set_state service go
          straight to storage and bypass the bounds check Home Assistant's
          own number.set_value service performs before calling
          async_set_native_value, so an out-of-range value (e.g. 11 with a
          declared max of 10) was accepted and published unchanged.
        """
        if item.entity_type in ("switch", "binary_sensor"):
            if isinstance(state, str):
                normalized = state.strip().lower()
                if normalized in ("false", "0", "off", "no", "non", ""):
                    return False
                if normalized in ("true", "1", "on", "yes", "oui"):
                    return True
            return bool(state)
        if item.entity_type == "number":
            try:
                value = float(state)
            except (TypeError, ValueError) as err:
                raise ValueError(f"Invalid numeric state for {item.item_id!r}: {state!r}") from err
            if item.min_value is not None and value < item.min_value:
                raise ValueError(
                    f"{value} is below the minimum ({item.min_value}) for {item.item_id!r}"
                )
            if item.max_value is not None and value > item.max_value:
                raise ValueError(
                    f"{value} is above the maximum ({item.max_value}) for {item.item_id!r}"
                )
            return value
        return state

    def snapshot(self) -> list[dict[str, Any]]:
        return [asdict(x) for x in self.items.values()]
