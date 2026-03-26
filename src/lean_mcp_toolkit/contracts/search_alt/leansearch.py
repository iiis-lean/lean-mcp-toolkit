"""Contracts for search_alt.leansearch."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import SearchAltRequest

SearchAltLeanSearchRequest = SearchAltRequest


@dataclass(slots=True, frozen=True)
class LeanSearchItem(DictModel):
    name: str
    module_name: str
    kind: str | None = None
    type: str | None = None
    formal_statement: str | None = None
    informal_name: str | None = None
    informal_description: str | None = None
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanSearchItem":
        raw_payload = data.get("raw_payload")
        return cls(
            name=str(data.get("name") or ""),
            module_name=str(data.get("module_name") or ""),
            kind=str(data["kind"]) if data.get("kind") is not None else None,
            type=str(data["type"]) if data.get("type") is not None else None,
            formal_statement=(
                str(data["formal_statement"])
                if data.get("formal_statement") is not None
                else None
            ),
            informal_name=(
                str(data["informal_name"]) if data.get("informal_name") is not None else None
            ),
            informal_description=(
                str(data["informal_description"])
                if data.get("informal_description") is not None
                else None
            ),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(slots=True, frozen=True)
class SearchAltLeanSearchResponse(DictModel):
    success: bool
    error_message: str | None
    query: str
    provider: str = "leansearch"
    backend_mode: str = "remote"
    items: tuple[LeanSearchItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltLeanSearchResponse":
        items = tuple(
            LeanSearchItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            query=str(data.get("query") or ""),
            provider=str(data.get("provider") or "leansearch"),
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
