"""Contracts for diagnostics.file."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int
from .common import DiagnosticItem


@dataclass(slots=True, frozen=True)
class FileRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    include_content: bool | None = None
    context_lines: int | None = None
    timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "FileRequest":
        include_content = (
            to_bool(data.get("include_content"), default=True)
            if "include_content" in data
            else None
        )
        context_lines = (
            to_int(data.get("context_lines"), default=2)
            if "context_lines" in data
            else None
        )
        timeout_seconds = (
            to_int(data.get("timeout_seconds"), default=None)
            if "timeout_seconds" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            include_content=include_content,
            context_lines=context_lines,
            timeout_seconds=timeout_seconds,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "include_content": self.include_content,
            "context_lines": self.context_lines,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class FileResponse(DictModel):
    success: bool
    error_message: str | None = None
    file: str = ""
    items: tuple[DiagnosticItem, ...] = field(default_factory=tuple)
    total_items: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    sorry_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "FileResponse":
        parsed_items: list[DiagnosticItem] = []
        raw_items = data.get("items")
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    parsed_items.append(DiagnosticItem.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            file=str(data.get("file") or ""),
            items=tuple(parsed_items),
            total_items=int(data.get("total_items") or 0),
            error_count=int(data.get("error_count") or 0),
            warning_count=int(data.get("warning_count") or 0),
            info_count=int(data.get("info_count") or 0),
            sorry_count=int(data.get("sorry_count") or 0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "file": self.file,
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "sorry_count": self.sorry_count,
        }

    def to_markdown(self, *, title: str | None = "File Diagnostics", title_level: int = 2) -> str:
        chunks: list[str] = []
        if title:
            chunks.append(f"{'#' * max(1, title_level)} {title}")
        chunks.append(f"- success: `{str(self.success).lower()}`")
        chunks.append(f"- file: `{self.file}`")
        if self.error_message:
            chunks.append(f"- error_message: {self.error_message}")
        chunks.append(f"- total_items: `{self.total_items}`")
        chunks.append(f"- error_count: `{self.error_count}`")
        chunks.append(f"- warning_count: `{self.warning_count}`")
        chunks.append(f"- info_count: `{self.info_count}`")
        chunks.append(f"- sorry_count: `{self.sorry_count}`")
        if self.items:
            chunks.append("")
            chunks.extend(item.to_markdown() for item in self.items)
        return "\n".join(chunks)

