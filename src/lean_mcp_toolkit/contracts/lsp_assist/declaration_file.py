"""Contracts for lsp.declaration_file."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict, to_bool, to_int
from .common import Position, Range


@dataclass(frozen=True)
class LspDeclarationFileRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    symbol: str = ""
    line: int | None = None
    column: int | None = None
    include_file_content: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationFileRequest":
        include_file_content = (
            to_bool(data.get("include_file_content"), default=False)
            if "include_file_content" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            symbol=str(data.get("symbol") or ""),
            line=to_int(data.get("line"), default=None),
            column=to_int(data.get("column"), default=None),
            include_file_content=include_file_content,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "line": self.line,
            "column": self.column,
            "include_file_content": self.include_file_content,
        }


@dataclass(frozen=True)
class LspDeclarationFileResponse(DictModel):
    success: bool
    error_message: str | None = None
    source_pos: Position | None = None
    target_file_path: str | None = None
    target_file_uri: str | None = None
    target_range: Range | None = None
    target_selection_range: Range | None = None
    content: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationFileResponse":
        source_pos = data.get("source_pos")
        target_range = data.get("target_range")
        target_selection_range = data.get("target_selection_range")
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            source_pos=Position.from_dict(source_pos) if isinstance(source_pos, dict) else None,
            target_file_path=(
                str(data["target_file_path"])
                if data.get("target_file_path") is not None
                else None
            ),
            target_file_uri=(
                str(data["target_file_uri"])
                if data.get("target_file_uri") is not None
                else None
            ),
            target_range=Range.from_dict(target_range) if isinstance(target_range, dict) else None,
            target_selection_range=(
                Range.from_dict(target_selection_range)
                if isinstance(target_selection_range, dict)
                else None
            ),
            content=(str(data["content"]) if data.get("content") is not None else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "source_pos": self.source_pos.to_dict() if self.source_pos is not None else None,
            "target_file_path": self.target_file_path,
            "target_file_uri": self.target_file_uri,
            "target_range": self.target_range.to_dict() if self.target_range is not None else None,
            "target_selection_range": (
                self.target_selection_range.to_dict()
                if self.target_selection_range is not None
                else None
            ),
            "content": self.content,
        }

