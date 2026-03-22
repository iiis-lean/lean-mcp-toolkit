"""Contracts for lsp.term_goal."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict, to_int


@dataclass(slots=True, frozen=True)
class LspTermGoalRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1
    column: int | None = None
    response_format: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspTermGoalRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=(to_int(data.get("line"), default=1) or 1),
            column=to_int(data.get("column"), default=None),
            response_format=(
                str(data["response_format"]) if data.get("response_format") is not None else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "response_format": self.response_format,
        }


@dataclass(slots=True, frozen=True)
class LspTermGoalResponse(DictModel):
    success: bool
    error_message: str | None = None
    line_context: str | None = None
    expected_type: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspTermGoalResponse":
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            line_context=(
                str(data["line_context"]) if data.get("line_context") is not None else None
            ),
            expected_type=(
                str(data["expected_type"]) if data.get("expected_type") is not None else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "line_context": self.line_context,
            "expected_type": self.expected_type,
        }
