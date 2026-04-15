"""Contracts for lsp.code_actions."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int


@dataclass(frozen=True)
class LspCodeActionsRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCodeActionsRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=(to_int(data.get("line"), default=1) or 1),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
        }


@dataclass(frozen=True)
class CodeActionEdit(DictModel):
    new_text: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CodeActionEdit":
        return cls(
            new_text=str(data.get("new_text") or ""),
            start_line=int(data.get("start_line") or 0),
            start_column=int(data.get("start_column") or 0),
            end_line=int(data.get("end_line") or 0),
            end_column=int(data.get("end_column") or 0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "new_text": self.new_text,
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass(frozen=True)
class CodeAction(DictModel):
    title: str
    is_preferred: bool
    edits: tuple[CodeActionEdit, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CodeAction":
        parsed_edits: list[CodeActionEdit] = []
        raw = data.get("edits")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed_edits.append(CodeActionEdit.from_dict(item))
        return cls(
            title=str(data.get("title") or ""),
            is_preferred=to_bool(data.get("is_preferred"), default=False),
            edits=tuple(parsed_edits),
        )

    def to_dict(self) -> JsonDict:
        return {
            "title": self.title,
            "is_preferred": self.is_preferred,
            "edits": [item.to_dict() for item in self.edits],
        }


@dataclass(frozen=True)
class LspCodeActionsResponse(DictModel):
    success: bool
    error_message: str | None = None
    actions: tuple[CodeAction, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCodeActionsResponse":
        parsed: list[CodeAction] = []
        raw = data.get("actions")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(CodeAction.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            actions=tuple(parsed),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "actions": [item.to_dict() for item in self.actions],
        }
