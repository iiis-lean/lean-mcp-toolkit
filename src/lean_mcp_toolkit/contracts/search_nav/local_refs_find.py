"""Contracts for repo_nav.local_refs.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_context_lines, parse_limit, parse_scopes, to_opt_str


@dataclass(frozen=True)
class LocalRefsFindRequest(DictModel):
    repo_root: str | None = None
    symbol: str = ""
    include_definition_site: bool | None = None
    scopes: tuple[str, ...] | None = None
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None
    context_lines: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalRefsFindRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            symbol=str(data.get("symbol") or ""),
            include_definition_site=(
                to_bool(data.get("include_definition_site"), default=False)
                if "include_definition_site" in data
                else None
            ),
            scopes=parse_scopes(data.get("scopes")),
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
            "symbol": self.symbol,
            "include_definition_site": self.include_definition_site,
            "scopes": list(self.scopes) if self.scopes is not None else None,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
            "context_lines": self.context_lines,
        }


@dataclass(frozen=True)
class LocalRefsFindItem(DictModel):
    file_path: str
    module_path: str | None
    line_start: int
    column_start: int | None
    scope: str
    snippet: str
    is_definition_site: bool
    matched_as: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalRefsFindItem":
        return cls(
            file_path=str(data.get("file_path") or ""),
            module_path=to_opt_str(data, "module_path"),
            line_start=int(data.get("line_start") or 0),
            column_start=(
                int(data["column_start"])
                if data.get("column_start") is not None
                else None
            ),
            scope=str(data.get("scope") or ""),
            snippet=str(data.get("snippet") or ""),
            is_definition_site=to_bool(data.get("is_definition_site"), default=False),
            matched_as=str(data.get("matched_as") or "tail_name"),
        )


@dataclass(frozen=True)
class LocalRefsFindResponse(DictModel):
    success: bool
    error_message: str | None = None
    symbol: str = ""
    count: int = 0
    items: tuple[LocalRefsFindItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalRefsFindResponse":
        raw_items = data.get("items")
        items: list[LocalRefsFindItem] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(LocalRefsFindItem.from_dict(item))

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            symbol=str(data.get("symbol") or ""),
            count=int(data.get("count") or len(items)),
            items=tuple(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "symbol": self.symbol,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


__all__ = ["LocalRefsFindRequest", "LocalRefsFindItem", "LocalRefsFindResponse"]
