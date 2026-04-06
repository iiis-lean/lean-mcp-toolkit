"""Contracts for leanfinder."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import SearchAltRequest

SearchAltLeanFinderRequest = SearchAltRequest


@dataclass(slots=True, frozen=True)
class LeanFinderItem(DictModel):
    full_name: str
    formal_statement: str
    informal_statement: str
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanFinderItem":
        raw_payload = data.get("raw_payload")
        return cls(
            full_name=str(data.get("full_name") or ""),
            formal_statement=str(data.get("formal_statement") or ""),
            informal_statement=str(data.get("informal_statement") or ""),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(slots=True, frozen=True)
class SearchAltLeanFinderResponse(DictModel):
    success: bool
    error_message: str | None
    query: str
    provider: str = "leanfinder"
    backend_mode: str = "remote"
    items: tuple[LeanFinderItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltLeanFinderResponse":
        items = tuple(
            LeanFinderItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            query=str(data.get("query") or ""),
            provider=str(data.get("provider") or "leanfinder"),
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
