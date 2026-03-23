"""Contracts for search.repo_nav.read."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict, to_bool
from .common import parse_int_or_none, to_opt_str
from .repo_nav_file_outline import RepoNavTarget


@dataclass(slots=True, frozen=True)
class RepoNavReadRequest(DictModel):
    repo_root: str | None = None
    target: str = ""
    start_line: int | None = None
    end_line: int | None = None
    max_lines: int | None = None
    with_line_numbers: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavReadRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            target=str(data.get("target") or ""),
            start_line=parse_int_or_none(data.get("start_line")),
            end_line=parse_int_or_none(data.get("end_line")),
            max_lines=parse_int_or_none(data.get("max_lines")),
            with_line_numbers=(
                to_bool(data.get("with_line_numbers"), default=True)
                if "with_line_numbers" in data
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "target": self.target,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "max_lines": self.max_lines,
            "with_line_numbers": self.with_line_numbers,
        }


@dataclass(slots=True, frozen=True)
class RepoNavReadWindow(DictModel):
    start_line: int
    end_line: int
    total_lines: int
    truncated: bool
    next_start_line: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavReadWindow":
        return cls(
            start_line=int(data.get("start_line") or 0),
            end_line=int(data.get("end_line") or 0),
            total_lines=int(data.get("total_lines") or 0),
            truncated=to_bool(data.get("truncated"), default=False),
            next_start_line=parse_int_or_none(data.get("next_start_line")),
        )


@dataclass(slots=True, frozen=True)
class RepoNavReadResponse(DictModel):
    success: bool
    error_message: str | None = None
    target: RepoNavTarget | None = None
    window: RepoNavReadWindow | None = None
    content: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavReadResponse":
        target_raw = data.get("target")
        window_raw = data.get("window")
        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            target=RepoNavTarget.from_dict(target_raw) if isinstance(target_raw, dict) else None,
            window=(
                RepoNavReadWindow.from_dict(window_raw)
                if isinstance(window_raw, dict)
                else None
            ),
            content=str(data.get("content") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "target": self.target.to_dict() if self.target else None,
            "window": self.window.to_dict() if self.window else None,
            "content": self.content,
        }


__all__ = [
    "RepoNavReadRequest",
    "RepoNavReadWindow",
    "RepoNavReadResponse",
]
