"""Contracts for repo_nav.local_decl.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_limit, parse_match_mode, parse_scopes, to_opt_str


@dataclass(slots=True, frozen=True)
class LocalDeclFindRequest(DictModel):
    repo_root: str | None = None
    query: str = ""
    match_mode: str = "prefix"
    decl_kinds: tuple[str, ...] | None = None
    namespace_filter: str | None = None
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclFindRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            query=str(data.get("query") or ""),
            match_mode=parse_match_mode(data.get("match_mode"), default="prefix"),
            decl_kinds=parse_scopes(data.get("decl_kinds")),
            namespace_filter=to_opt_str(data, "namespace_filter"),
            module_filter=to_opt_str(data, "module_filter"),
            include_deps=(
                to_bool(data.get("include_deps"), default=False)
                if "include_deps" in data
                else None
            ),
            limit=parse_limit(data.get("limit"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "query": self.query,
            "match_mode": self.match_mode,
            "decl_kinds": list(self.decl_kinds) if self.decl_kinds is not None else None,
            "namespace_filter": self.namespace_filter,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
        }


@dataclass(slots=True, frozen=True)
class LocalDeclFindItem(DictModel):
    full_name: str
    short_name: str
    decl_kind: str
    module_path: str | None
    file_path: str
    line_start: int
    line_end: int | None = None
    header_preview: str | None = None
    visibility: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclFindItem":
        return cls(
            full_name=str(data.get("full_name") or ""),
            short_name=str(data.get("short_name") or ""),
            decl_kind=str(data.get("decl_kind") or ""),
            module_path=to_opt_str(data, "module_path"),
            file_path=str(data.get("file_path") or ""),
            line_start=int(data.get("line_start") or 0),
            line_end=(int(data["line_end"]) if data.get("line_end") is not None else None),
            header_preview=to_opt_str(data, "header_preview"),
            visibility=to_opt_str(data, "visibility"),
        )


@dataclass(slots=True, frozen=True)
class LocalDeclFindResponse(DictModel):
    success: bool
    error_message: str | None = None
    query: str = ""
    count: int = 0
    items: tuple[LocalDeclFindItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclFindResponse":
        raw_items = data.get("items")
        items: list[LocalDeclFindItem] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(LocalDeclFindItem.from_dict(item))

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


__all__ = ["LocalDeclFindRequest", "LocalDeclFindItem", "LocalDeclFindResponse"]
