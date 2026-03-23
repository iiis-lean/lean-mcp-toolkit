"""Contracts for search.mathlib_nav.read."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict
from ..search_nav import RepoNavReadResponse, RepoNavReadWindow, RepoNavTarget
from ..search_nav.common import parse_int_or_none, to_opt_str


@dataclass(slots=True, frozen=True)
class MathlibNavReadRequest(DictModel):
    project_root: str | None = None
    mathlib_root: str | None = None
    target: str = ""
    start_line: int | None = None
    end_line: int | None = None
    max_lines: int | None = None
    with_line_numbers: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibNavReadRequest":
        return cls(
            project_root=to_opt_str(data, "project_root"),
            mathlib_root=to_opt_str(data, "mathlib_root"),
            target=str(data.get("target") or ""),
            start_line=parse_int_or_none(data.get("start_line")),
            end_line=parse_int_or_none(data.get("end_line")),
            max_lines=parse_int_or_none(data.get("max_lines")),
            with_line_numbers=(
                bool(data["with_line_numbers"]) if "with_line_numbers" in data else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "mathlib_root": self.mathlib_root,
            "target": self.target,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "max_lines": self.max_lines,
            "with_line_numbers": self.with_line_numbers,
        }


MathlibNavTarget = RepoNavTarget
MathlibNavReadWindow = RepoNavReadWindow
MathlibNavReadResponse = RepoNavReadResponse


__all__ = [
    "MathlibNavReadRequest",
    "MathlibNavTarget",
    "MathlibNavReadWindow",
    "MathlibNavReadResponse",
]
