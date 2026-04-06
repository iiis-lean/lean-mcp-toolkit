"""Contracts for mathlib_nav.grep."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict
from ..search_nav import LocalTextFindItem, RepoNavGrepResponse
from ..search_nav.common import parse_context_lines, parse_limit, parse_scopes, parse_text_match, to_opt_str


@dataclass(slots=True, frozen=True)
class MathlibNavGrepRequest(DictModel):
    project_root: str | None = None
    mathlib_root: str | None = None
    query: str = ""
    match_mode: str = "phrase"
    base: str | None = None
    target: str | None = None
    context_lines: int | None = None
    limit: int | None = None
    scopes: tuple[str, ...] | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibNavGrepRequest":
        return cls(
            project_root=to_opt_str(data, "project_root"),
            mathlib_root=to_opt_str(data, "mathlib_root"),
            query=str(data.get("query") or ""),
            match_mode=parse_text_match(data.get("match_mode"), default="phrase"),
            base=to_opt_str(data, "base"),
            target=to_opt_str(data, "target"),
            context_lines=parse_context_lines(data.get("context_lines"), default=None),
            limit=parse_limit(data.get("limit"), default=None),
            scopes=parse_scopes(data.get("scopes")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "mathlib_root": self.mathlib_root,
            "query": self.query,
            "match_mode": self.match_mode,
            "base": self.base,
            "target": self.target,
            "context_lines": self.context_lines,
            "limit": self.limit,
            "scopes": list(self.scopes) if self.scopes is not None else None,
        }


MathlibNavGrepItem = LocalTextFindItem
MathlibNavGrepResponse = RepoNavGrepResponse


__all__ = [
    "MathlibNavGrepRequest",
    "MathlibNavGrepItem",
    "MathlibNavGrepResponse",
]
