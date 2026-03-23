"""Contracts for search.repo_nav.tree."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_int_or_none, parse_limit, to_opt_str


@dataclass(slots=True, frozen=True)
class RepoNavTreeRequest(DictModel):
    repo_root: str | None = None
    base: str | None = None
    depth: int | None = None
    name_filter: str | None = None
    limit: int | None = None
    offset: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavTreeRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            base=to_opt_str(data, "base"),
            depth=parse_int_or_none(data.get("depth")),
            name_filter=to_opt_str(data, "name_filter"),
            limit=parse_limit(data.get("limit"), default=None),
            offset=parse_int_or_none(data.get("offset")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "base": self.base,
            "depth": self.depth,
            "name_filter": self.name_filter,
            "limit": self.limit,
            "offset": self.offset,
        }


@dataclass(slots=True, frozen=True)
class RepoNavResolution(DictModel):
    repo_root: str
    source_root: str
    base_path: str
    base_module: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavResolution":
        return cls(
            repo_root=str(data.get("repo_root") or ""),
            source_root=str(data.get("source_root") or ""),
            base_path=str(data.get("base_path") or ""),
            base_module=to_opt_str(data, "base_module"),
        )


@dataclass(slots=True, frozen=True)
class RepoNavTreeEntry(DictModel):
    kind: str
    name: str
    relative_path: str
    module_path: str | None = None
    has_children: bool = False
    child_count: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavTreeEntry":
        return cls(
            kind=str(data.get("kind") or "file"),
            name=str(data.get("name") or ""),
            relative_path=str(data.get("relative_path") or ""),
            module_path=to_opt_str(data, "module_path"),
            has_children=to_bool(data.get("has_children"), default=False),
            child_count=parse_int_or_none(data.get("child_count")),
        )


@dataclass(slots=True, frozen=True)
class RepoNavTreePage(DictModel):
    offset: int
    limit: int
    returned: int
    next_offset: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavTreePage":
        return cls(
            offset=parse_int_or_none(data.get("offset")) or 0,
            limit=parse_int_or_none(data.get("limit")) or 0,
            returned=parse_int_or_none(data.get("returned")) or 0,
            next_offset=parse_int_or_none(data.get("next_offset")),
        )


@dataclass(slots=True, frozen=True)
class RepoNavTreeResponse(DictModel):
    success: bool
    error_message: str | None = None
    resolution: RepoNavResolution | None = None
    entries: tuple[RepoNavTreeEntry, ...] = field(default_factory=tuple)
    page: RepoNavTreePage | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavTreeResponse":
        raw_entries = data.get("entries")
        entries: list[RepoNavTreeEntry] = []
        if isinstance(raw_entries, list):
            for item in raw_entries:
                if isinstance(item, dict):
                    entries.append(RepoNavTreeEntry.from_dict(item))

        resolution_raw = data.get("resolution")
        page_raw = data.get("page")

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            resolution=(
                RepoNavResolution.from_dict(resolution_raw)
                if isinstance(resolution_raw, dict)
                else None
            ),
            entries=tuple(entries),
            page=RepoNavTreePage.from_dict(page_raw) if isinstance(page_raw, dict) else None,
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "resolution": self.resolution.to_dict() if self.resolution else None,
            "entries": [entry.to_dict() for entry in self.entries],
            "page": self.page.to_dict() if self.page else None,
        }


__all__ = [
    "RepoNavTreeRequest",
    "RepoNavResolution",
    "RepoNavTreeEntry",
    "RepoNavTreePage",
    "RepoNavTreeResponse",
]
