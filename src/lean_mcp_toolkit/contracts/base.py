"""Base protocols/helpers for shared contracts."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Protocol, TypeVar

JsonPrimitive = str | int | float | bool | None
# Use a non-recursive alias here so MCP/Pydantic schema generation for tool
# signatures does not trip over unresolved recursive dict/list unions.
JsonValue = Any
JsonDict = dict[str, Any]

T = TypeVar("T", bound="DictModel")


class MarkdownRenderable(Protocol):
    """Contract for models that can render markdown."""

    def to_markdown(self, *, title: str | None = None, title_level: int = 2) -> str:
        ...


class DictModel:
    """Simple dict-serializable dataclass base class."""

    @classmethod
    def from_dict(cls: type[T], data: JsonDict) -> T:
        raise NotImplementedError

    def to_dict(self) -> JsonDict:
        return asdict(self)  # type: ignore[return-value]



def to_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default



def to_int(value: Any, *, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default



def to_list_of_str(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]
