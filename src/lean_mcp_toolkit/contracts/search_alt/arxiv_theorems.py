"""Contracts for arXiv theorem search."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import SearchAltRequest

SearchAltArxivTheoremsRequest = SearchAltRequest


@dataclass(frozen=True)
class ArxivTheoremItem(DictModel):
    title: str
    theorem: str
    arxiv_id: str
    theorem_id: str
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ArxivTheoremItem":
        raw_payload = data.get("raw_payload")
        return cls(
            title=str(data.get("title") or ""),
            theorem=str(data.get("theorem") or ""),
            arxiv_id=str(data.get("arxiv_id") or ""),
            theorem_id=str(data.get("theorem_id") or ""),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(frozen=True)
class SearchAltArxivTheoremsResponse(DictModel):
    success: bool
    error_message: str | None
    query: str
    provider: str = "arxiv_theorems"
    backend_mode: str = "remote"
    items: tuple[ArxivTheoremItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltArxivTheoremsResponse":
        items = tuple(
            ArxivTheoremItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            query=str(data.get("query") or ""),
            provider=str(data.get("provider") or "arxiv_theorems"),
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
