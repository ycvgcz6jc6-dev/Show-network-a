"""Bounded runtime state store, independent from Home Assistant entities."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

class RuntimeStateStore:
    """Own normalized runtime state without knowing HA entity semantics."""
    def __init__(self, initial: dict[str, Any] | None = None, history_limit: int = 100, max_keys: int = 512) -> None:
        self._state = dict(initial or {})
        self.max_keys = max(1, int(max_keys))
        self._history: list[dict[str, Any]] = []
        self.history_limit = max(1, int(history_limit))

    def update(self, **values: Any) -> None:
        self._state.update(values)
        if len(self._state) > self.max_keys:
            # Keep the newest update keys; stale keys are not allowed to grow memory forever.
            protected = set(values)
            for key in list(self._state):
                if len(self._state) <= self.max_keys:
                    break
                if key not in protected:
                    self._state.pop(key, None)
        self._history.append(dict(values))
        if len(self._history) > self.history_limit:
            del self._history[:-self.history_limit]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def history(self) -> list[dict[str, Any]]:
        return deepcopy(self._history)
