"""Common contracts for search_alt tools."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict, to_int


@dataclass(frozen=True)
class SearchAltRequest(DictModel):
    query: str = ""
    num_results: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltRequest":
        return cls(
            query=str(data.get("query") or ""),
            num_results=to_int(data.get("num_results"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {"query": self.query, "num_results": self.num_results}
