"""Contracts for lsp.hover."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int
from .common import DiagnosticMessage, diagnostics_to_dict, parse_diagnostics


@dataclass(slots=True, frozen=True)
class LspHoverRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1
    column: int = 1
    include_diagnostics: bool | None = None
    response_format: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspHoverRequest":
        include_diagnostics = (
            to_bool(data.get("include_diagnostics"), default=True)
            if "include_diagnostics" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=(to_int(data.get("line"), default=1) or 1),
            column=(to_int(data.get("column"), default=1) or 1),
            include_diagnostics=include_diagnostics,
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
            "include_diagnostics": self.include_diagnostics,
            "response_format": self.response_format,
        }


@dataclass(slots=True, frozen=True)
class LspHoverResponse(DictModel):
    success: bool
    error_message: str | None = None
    symbol: str | None = None
    info: str | None = None
    diagnostics: tuple[DiagnosticMessage, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspHoverResponse":
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            symbol=(str(data["symbol"]) if data.get("symbol") is not None else None),
            info=(str(data["info"]) if data.get("info") is not None else None),
            diagnostics=parse_diagnostics(data.get("diagnostics")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "symbol": self.symbol,
            "info": self.info,
            "diagnostics": diagnostics_to_dict(self.diagnostics),
        }
