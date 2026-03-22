"""Runtime backend instance container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BackendContext:
    """Container for initialized backend instances."""

    _instances: dict[str, Any] = field(default_factory=dict, repr=False)

    def set(self, key: str, value: Any) -> None:
        self._instances[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._instances.get(key, default)

    def require(self, key: str) -> Any:
        if key not in self._instances:
            raise KeyError(f"backend not initialized: {key}")
        return self._instances[key]

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._instances.keys()))


__all__ = ["BackendContext"]
