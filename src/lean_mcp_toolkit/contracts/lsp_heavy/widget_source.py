"""Contracts for lsp.widget_source."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict


@dataclass(frozen=True)
class LspWidgetSourceRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    javascript_hash: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspWidgetSourceRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            javascript_hash=str(data.get("javascript_hash") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "javascript_hash": self.javascript_hash,
        }


@dataclass(frozen=True)
class LspWidgetSourceResponse(DictModel):
    success: bool
    error_message: str | None = None
    javascript_hash: str = ""
    source_text: str | None = None
    raw_source: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspWidgetSourceResponse":
        raw_source = data.get("raw_source")
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            javascript_hash=str(data.get("javascript_hash") or ""),
            source_text=(
                str(data["source_text"]) if data.get("source_text") is not None else None
            ),
            raw_source=dict(raw_source) if isinstance(raw_source, dict) else None,
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "javascript_hash": self.javascript_hash,
            "source_text": self.source_text,
            "raw_source": dict(self.raw_source) if isinstance(self.raw_source, dict) else None,
        }
