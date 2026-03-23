"""Contracts for search.local_text.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_context_lines, parse_limit, parse_scopes, parse_text_match, to_opt_str


@dataclass(slots=True, frozen=True)
class LocalTextFindRequest(DictModel):
    repo_root: str | None = None
    query: str = ""
    scopes: tuple[str, ...] | None = None
    text_match: str = "phrase"
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None
    context_lines: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalTextFindRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            query=str(data.get("query") or ""),
            scopes=parse_scopes(data.get("scopes")),
            text_match=parse_text_match(data.get("text_match"), default="phrase"),
            module_filter=to_opt_str(data, "module_filter"),
            include_deps=(
                to_bool(data.get("include_deps"), default=False)
                if "include_deps" in data
                else None
            ),
            limit=parse_limit(data.get("limit"), default=None),
            context_lines=parse_context_lines(data.get("context_lines"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "query": self.query,
            "scopes": list(self.scopes) if self.scopes is not None else None,
            "text_match": self.text_match,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
            "context_lines": self.context_lines,
        }


@dataclass(slots=True, frozen=True)
class LocalTextFindItem(DictModel):
    scope: str
    file_path: str
    module_path: str | None
    line_start: int
    line_end: int
    snippet: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalTextFindItem":
        return cls(
            scope=str(data.get("scope") or ""),
            file_path=str(data.get("file_path") or ""),
            module_path=to_opt_str(data, "module_path"),
            line_start=int(data.get("line_start") or 0),
            line_end=int(data.get("line_end") or 0),
            snippet=str(data.get("snippet") or ""),
        )


@dataclass(slots=True, frozen=True)
class LocalTextFindResponse(DictModel):
    success: bool
    error_message: str | None = None
    query: str = ""
    count: int = 0
    items: tuple[LocalTextFindItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalTextFindResponse":
        raw_items = data.get("items")
        items: list[LocalTextFindItem] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(LocalTextFindItem.from_dict(item))

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            query=str(data.get("query") or ""),
            count=int(data.get("count") or len(items)),
            items=tuple(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "query": self.query,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


__all__ = ["LocalTextFindRequest", "LocalTextFindItem", "LocalTextFindResponse"]
