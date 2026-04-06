"""Contracts for repo_nav.grep."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_context_lines, parse_limit, parse_scopes, parse_text_match, to_opt_str
from .local_text_find import LocalTextFindItem


@dataclass(slots=True, frozen=True)
class RepoNavGrepRequest(DictModel):
    repo_root: str | None = None
    query: str = ""
    match_mode: str = "phrase"
    path_filter: str | None = None
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None
    context_lines: int | None = None
    scopes: tuple[str, ...] | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavGrepRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            query=str(data.get("query") or ""),
            match_mode=parse_text_match(data.get("match_mode"), default="phrase"),
            path_filter=to_opt_str(data, "path_filter"),
            module_filter=to_opt_str(data, "module_filter"),
            include_deps=(
                to_bool(data.get("include_deps"), default=False)
                if "include_deps" in data
                else None
            ),
            limit=parse_limit(data.get("limit"), default=None),
            context_lines=parse_context_lines(data.get("context_lines"), default=None),
            scopes=parse_scopes(data.get("scopes")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "query": self.query,
            "match_mode": self.match_mode,
            "path_filter": self.path_filter,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
            "context_lines": self.context_lines,
            "scopes": list(self.scopes) if self.scopes is not None else None,
        }


@dataclass(slots=True, frozen=True)
class RepoNavGrepResponse(DictModel):
    success: bool
    error_message: str | None = None
    query: str = ""
    match_mode: str = "phrase"
    path_filter: str | None = None
    count: int = 0
    items: tuple[LocalTextFindItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavGrepResponse":
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
            match_mode=parse_text_match(data.get("match_mode"), default="phrase"),
            path_filter=to_opt_str(data, "path_filter"),
            count=int(data.get("count") or len(items)),
            items=tuple(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "query": self.query,
            "match_mode": self.match_mode,
            "path_filter": self.path_filter,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


__all__ = ["RepoNavGrepRequest", "RepoNavGrepResponse"]
