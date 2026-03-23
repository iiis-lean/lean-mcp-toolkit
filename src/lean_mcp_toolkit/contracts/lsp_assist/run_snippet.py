"""Contracts for lsp.run_snippet."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import DiagnosticMessage


@dataclass(slots=True, frozen=True)
class LspRunSnippetRequest(DictModel):
    project_root: str | None = None
    code: str = ""
    timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspRunSnippetRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            code=str(data.get("code") or ""),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "code": self.code,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class LspRunSnippetResponse(DictModel):
    success: bool
    error_message: str | None = None
    diagnostics: tuple[DiagnosticMessage, ...] = field(default_factory=tuple)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspRunSnippetResponse":
        parsed: list[DiagnosticMessage] = []
        raw = data.get("diagnostics")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(DiagnosticMessage.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            diagnostics=tuple(parsed),
            error_count=int(data.get("error_count") or 0),
            warning_count=int(data.get("warning_count") or 0),
            info_count=int(data.get("info_count") or 0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
        }

