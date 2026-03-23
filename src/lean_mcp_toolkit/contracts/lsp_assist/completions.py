"""Contracts for lsp.completions."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int


@dataclass(slots=True, frozen=True)
class LspCompletionsRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 1
    column: int = 1
    max_completions: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCompletionsRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=to_int(data.get("line"), default=1) or 1,
            column=to_int(data.get("column"), default=1) or 1,
            max_completions=to_int(data.get("max_completions"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "max_completions": self.max_completions,
        }


@dataclass(slots=True, frozen=True)
class CompletionItem(DictModel):
    label: str
    kind: str | None = None
    detail: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CompletionItem":
        return cls(
            label=str(data.get("label") or ""),
            kind=(str(data["kind"]) if data.get("kind") is not None else None),
            detail=(str(data["detail"]) if data.get("detail") is not None else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "label": self.label,
            "kind": self.kind,
            "detail": self.detail,
        }


@dataclass(slots=True, frozen=True)
class LspCompletionsResponse(DictModel):
    success: bool
    error_message: str | None = None
    items: tuple[CompletionItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCompletionsResponse":
        parsed: list[CompletionItem] = []
        raw = data.get("items")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(CompletionItem.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            items=tuple(parsed),
            count=int(data.get("count") or len(parsed)),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
        }

