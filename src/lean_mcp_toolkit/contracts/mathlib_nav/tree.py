"""Contracts for search.mathlib_nav.tree."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict
from ..search_nav import RepoNavResolution, RepoNavTreeEntry, RepoNavTreePage, RepoNavTreeResponse
from ..search_nav.common import parse_int_or_none, parse_limit, to_opt_str


@dataclass(slots=True, frozen=True)
class MathlibNavTreeRequest(DictModel):
    project_root: str | None = None
    mathlib_root: str | None = None
    base: str | None = None
    depth: int | None = None
    name_filter: str | None = None
    limit: int | None = None
    offset: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibNavTreeRequest":
        return cls(
            project_root=to_opt_str(data, "project_root"),
            mathlib_root=to_opt_str(data, "mathlib_root"),
            base=to_opt_str(data, "base"),
            depth=parse_int_or_none(data.get("depth")),
            name_filter=to_opt_str(data, "name_filter"),
            limit=parse_limit(data.get("limit"), default=None),
            offset=parse_int_or_none(data.get("offset")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "mathlib_root": self.mathlib_root,
            "base": self.base,
            "depth": self.depth,
            "name_filter": self.name_filter,
            "limit": self.limit,
            "offset": self.offset,
        }


MathlibNavResolution = RepoNavResolution
MathlibNavTreeEntry = RepoNavTreeEntry
MathlibNavTreePage = RepoNavTreePage
MathlibNavTreeResponse = RepoNavTreeResponse


__all__ = [
    "MathlibNavTreeRequest",
    "MathlibNavResolution",
    "MathlibNavTreeEntry",
    "MathlibNavTreePage",
    "MathlibNavTreeResponse",
]
