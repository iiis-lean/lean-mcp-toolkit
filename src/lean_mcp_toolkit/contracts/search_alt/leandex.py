"""Contracts for search_alt.leandex."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import SearchAltRequest

SearchAltLeanDexRequest = SearchAltRequest


@dataclass(slots=True, frozen=True)
class LeanDexItem(DictModel):
    primary_declaration: str
    source_file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    statement: str | None = None
    full_statement: str | None = None
    docstring: str | None = None
    informal_description: str | None = None
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanDexItem":
        raw_payload = data.get("raw_payload")
        return cls(
            primary_declaration=str(data.get("primary_declaration") or ""),
            source_file=str(data["source_file"]) if data.get("source_file") is not None else None,
            start_line=to_int(data.get("start_line"), default=None),
            end_line=to_int(data.get("end_line"), default=None),
            statement=str(data["statement"]) if data.get("statement") is not None else None,
            full_statement=(
                str(data["full_statement"]) if data.get("full_statement") is not None else None
            ),
            docstring=str(data["docstring"]) if data.get("docstring") is not None else None,
            informal_description=(
                str(data["informal_description"])
                if data.get("informal_description") is not None
                else None
            ),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(slots=True, frozen=True)
class SearchAltLeanDexResponse(DictModel):
    success: bool
    error_message: str | None
    query: str
    provider: str = "leandex"
    backend_mode: str = "remote"
    items: tuple[LeanDexItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltLeanDexResponse":
        items = tuple(
            LeanDexItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            query=str(data.get("query") or ""),
            provider=str(data.get("provider") or "leandex"),
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
