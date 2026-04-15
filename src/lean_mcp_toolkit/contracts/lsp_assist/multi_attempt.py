"""Contracts for lsp.multi_attempt."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int, to_list_of_str
from .common import DiagnosticMessage


@dataclass(frozen=True)
class LspMultiAttemptRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1
    snippets: tuple[str, ...] = field(default_factory=tuple)
    max_attempts: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspMultiAttemptRequest":
        snippets = to_list_of_str(data.get("snippets")) or []
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=to_int(data.get("line"), default=1) or 1,
            snippets=tuple(snippets),
            max_attempts=to_int(data.get("max_attempts"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "snippets": list(self.snippets),
            "max_attempts": self.max_attempts,
        }


@dataclass(frozen=True)
class AttemptResult(DictModel):
    snippet: str
    goals: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: tuple[DiagnosticMessage, ...] = field(default_factory=tuple)
    attempt_success: bool = False
    goal_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AttemptResult":
        raw_goals = data.get("goals")
        goals: list[str] = []
        if isinstance(raw_goals, list):
            goals = [str(item) for item in raw_goals]

        parsed_diags: list[DiagnosticMessage] = []
        raw_diags = data.get("diagnostics")
        if isinstance(raw_diags, list):
            for item in raw_diags:
                if isinstance(item, dict):
                    parsed_diags.append(DiagnosticMessage.from_dict(item))

        return cls(
            snippet=str(data.get("snippet") or ""),
            goals=tuple(goals),
            diagnostics=tuple(parsed_diags),
            attempt_success=bool(data.get("attempt_success", False)),
            goal_count=int(data.get("goal_count") or len(goals)),
        )

    def to_dict(self) -> JsonDict:
        return {
            "snippet": self.snippet,
            "goals": list(self.goals),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "attempt_success": self.attempt_success,
            "goal_count": self.goal_count,
        }


@dataclass(frozen=True)
class LspMultiAttemptResponse(DictModel):
    success: bool
    error_message: str | None = None
    items: tuple[AttemptResult, ...] = field(default_factory=tuple)
    count: int = 0
    any_success: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspMultiAttemptResponse":
        parsed: list[AttemptResult] = []
        raw = data.get("items")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(AttemptResult.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            items=tuple(parsed),
            count=int(data.get("count") or len(parsed)),
            any_success=bool(data.get("any_success", False)),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
            "any_success": self.any_success,
        }

