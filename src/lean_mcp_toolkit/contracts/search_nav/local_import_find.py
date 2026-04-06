"""Contracts for repo_nav.local_import.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_import_direction, parse_limit, parse_match_mode, to_opt_str


@dataclass(slots=True, frozen=True)
class LocalImportFindRequest(DictModel):
    repo_root: str | None = None
    query: str = ""
    match_mode: str = "exact"
    direction: str = "imported_by"
    module_filter: str | None = None
    include_deps: bool | None = None
    limit: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalImportFindRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            query=str(data.get("query") or ""),
            match_mode=parse_match_mode(data.get("match_mode"), default="exact"),
            direction=parse_import_direction(data.get("direction"), default="imported_by"),
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
            "direction": self.direction,
            "module_filter": self.module_filter,
            "include_deps": self.include_deps,
            "limit": self.limit,
        }


@dataclass(slots=True, frozen=True)
class LocalImportEdgeItem(DictModel):
    importer_module: str | None
    importer_file: str
    imported_module: str
    line_start: int
    line_end: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalImportEdgeItem":
        return cls(
            importer_module=to_opt_str(data, "importer_module"),
            importer_file=str(data.get("importer_file") or ""),
            imported_module=str(data.get("imported_module") or ""),
            line_start=int(data.get("line_start") or 0),
            line_end=int(data.get("line_end") or 0),
        )


@dataclass(slots=True, frozen=True)
class LocalImportFindResponse(DictModel):
    success: bool
    error_message: str | None = None
    query: str = ""
    count: int = 0
    edges: tuple[LocalImportEdgeItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalImportFindResponse":
        raw_edges = data.get("edges")
        edges: list[LocalImportEdgeItem] = []
        if isinstance(raw_edges, list):
            for item in raw_edges:
                if isinstance(item, dict):
                    edges.append(LocalImportEdgeItem.from_dict(item))

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            query=str(data.get("query") or ""),
            count=int(data.get("count") or len(edges)),
            edges=tuple(edges),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "query": self.query,
            "count": self.count,
            "edges": [item.to_dict() for item in self.edges],
        }


__all__ = [
    "LocalImportFindRequest",
    "LocalImportEdgeItem",
    "LocalImportFindResponse",
]
