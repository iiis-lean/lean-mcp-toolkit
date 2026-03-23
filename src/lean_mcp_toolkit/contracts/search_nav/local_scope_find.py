"""Contracts for search.local_scope.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_context_lines, parse_limit, parse_match_mode, parse_scopes, to_opt_str


@dataclass(slots=True, frozen=True)
class LocalScopeFindRequest(DictModel):
    repo_root: str | None = None
    query: str | None = None
    scope_kinds: tuple[str, ...] | None = None
    match_mode: str = "prefix"
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None
    context_lines: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalScopeFindRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            query=to_opt_str(data, "query"),
            scope_kinds=parse_scopes(data.get("scope_kinds")),
            match_mode=parse_match_mode(data.get("match_mode"), default="prefix"),
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
            "scope_kinds": list(self.scope_kinds) if self.scope_kinds is not None else None,
            "match_mode": self.match_mode,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
            "context_lines": self.context_lines,
        }


@dataclass(slots=True, frozen=True)
class LocalScopeFindItem(DictModel):
    scope_kind: str
    target: str | None
    file_path: str
    module_path: str | None
    line_start: int
    line_end: int | None = None
    snippet: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalScopeFindItem":
        return cls(
            scope_kind=str(data.get("scope_kind") or ""),
            target=to_opt_str(data, "target"),
            file_path=str(data.get("file_path") or ""),
            module_path=to_opt_str(data, "module_path"),
            line_start=int(data.get("line_start") or 0),
            line_end=(int(data["line_end"]) if data.get("line_end") is not None else None),
            snippet=to_opt_str(data, "snippet"),
        )


@dataclass(slots=True, frozen=True)
class LocalScopeFindResponse(DictModel):
    success: bool
    error_message: str | None = None
    count: int = 0
    items: tuple[LocalScopeFindItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalScopeFindResponse":
        raw_items = data.get("items")
        items: list[LocalScopeFindItem] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(LocalScopeFindItem.from_dict(item))

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            count=int(data.get("count") or len(items)),
            items=tuple(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


__all__ = ["LocalScopeFindRequest", "LocalScopeFindItem", "LocalScopeFindResponse"]
