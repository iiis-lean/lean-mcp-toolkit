"""Contracts for lsp.goal."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int


@dataclass(frozen=True)
class LspGoalRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1
    column: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspGoalRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=(to_int(data.get("line"), default=1) or 1),
            column=to_int(data.get("column"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class LspGoalResponse(DictModel):
    success: bool
    error_message: str | None = None
    line_context: str | None = None
    goals: tuple[str, ...] | None = None
    goals_before: tuple[str, ...] | None = None
    goals_after: tuple[str, ...] | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspGoalResponse":
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            line_context=(
                str(data["line_context"]) if data.get("line_context") is not None else None
            ),
            goals=_to_tuple(data.get("goals")),
            goals_before=_to_tuple(data.get("goals_before")),
            goals_after=_to_tuple(data.get("goals_after")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "line_context": self.line_context,
            "goals": list(self.goals) if self.goals is not None else None,
            "goals_before": list(self.goals_before) if self.goals_before is not None else None,
            "goals_after": list(self.goals_after) if self.goals_after is not None else None,
        }


def _to_tuple(raw: object) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    return tuple()
