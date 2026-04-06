"""Contracts for loogle."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import SearchAltRequest

SearchAltLoogleRequest = SearchAltRequest


@dataclass(slots=True, frozen=True)
class LoogleItem(DictModel):
    name: str
    type: str
    module: str
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LoogleItem":
        raw_payload = data.get("raw_payload")
        return cls(
            name=str(data.get("name") or ""),
            type=str(data.get("type") or ""),
            module=str(data.get("module") or ""),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(slots=True, frozen=True)
class SearchAltLoogleResponse(DictModel):
    success: bool
    error_message: str | None
    query: str
    provider: str = "loogle"
    backend_mode: str = "remote"
    items: tuple[LoogleItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltLoogleResponse":
        items = tuple(
            LoogleItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            query=str(data.get("query") or ""),
            provider=str(data.get("provider") or "loogle"),
            backend_mode=str(data.get("backend_mode") or "remote"),
            items=items,
            count=to_int(data.get("count"), default=len(items)) or len(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "query": self.query,
            "provider": self.provider,
            "backend_mode": self.backend_mode,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
        }
