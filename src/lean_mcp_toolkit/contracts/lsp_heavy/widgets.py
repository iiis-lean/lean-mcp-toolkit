"""Contracts for lsp.widgets."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, JsonValue, to_int
from ..lsp_assist.common import Range


@dataclass(slots=True, frozen=True)
class LspWidgetsRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 0
    column: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspWidgetsRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=to_int(data.get("line"), default=0) or 0,
            column=to_int(data.get("column"), default=0) or 0,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
        }


@dataclass(slots=True, frozen=True)
class WidgetInstance(DictModel):
    widget_id: str
    javascript_hash: str | None = None
    name: str | None = None
    range: Range | None = None
    props: JsonValue = None
    raw: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WidgetInstance":
        raw_range = data.get("range")
        return cls(
            widget_id=str(data.get("widget_id") or ""),
            javascript_hash=(
                str(data["javascript_hash"]) if data.get("javascript_hash") is not None else None
            ),
            name=str(data["name"]) if data.get("name") is not None else None,
            range=Range.from_dict(raw_range) if isinstance(raw_range, dict) else None,
            props=data.get("props"),
            raw=dict(data.get("raw") or {}),
        )

    def to_dict(self) -> JsonDict:
        return {
            "widget_id": self.widget_id,
            "javascript_hash": self.javascript_hash,
            "name": self.name,
            "range": self.range.to_dict() if self.range is not None else None,
            "props": self.props,
            "raw": dict(self.raw),
        }


@dataclass(slots=True, frozen=True)
class LspWidgetsResponse(DictModel):
    success: bool
    error_message: str | None = None
    widgets: tuple[WidgetInstance, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspWidgetsResponse":
        items: list[WidgetInstance] = []
        raw = data.get("widgets")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    items.append(WidgetInstance.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            widgets=tuple(items),
            count=to_int(data.get("count"), default=len(items)) or len(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "widgets": [item.to_dict() for item in self.widgets],
            "count": self.count,
        }
