"""Contracts for lsp.proof_profile."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int


@dataclass(frozen=True)
class LspProofProfileRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 0
    top_n: int | None = None
    timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspProofProfileRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=to_int(data.get("line"), default=0) or 0,
            top_n=to_int(data.get("top_n"), default=None),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "top_n": self.top_n,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class ProfileLine(DictModel):
    line: int
    ms: float
    text: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProfileLine":
        return cls(
            line=int(data.get("line") or 0),
            ms=float(data.get("ms") or 0.0),
            text=str(data.get("text") or ""),
        )


@dataclass(frozen=True)
class ProfileCategory(DictModel):
    name: str
    ms: float

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProfileCategory":
        return cls(
            name=str(data.get("name") or ""),
            ms=float(data.get("ms") or 0.0),
        )


@dataclass(frozen=True)
class LspProofProfileResponse(DictModel):
    success: bool
    error_message: str | None = None
    theorem_name: str | None = None
    total_ms: float | None = None
    lines: tuple[ProfileLine, ...] = field(default_factory=tuple)
    count: int = 0
    categories: tuple[ProfileCategory, ...] = field(default_factory=tuple)
    category_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspProofProfileResponse":
        line_items: list[ProfileLine] = []
        raw_lines = data.get("lines")
        if isinstance(raw_lines, list):
            for item in raw_lines:
                if isinstance(item, dict):
                    line_items.append(ProfileLine.from_dict(item))
        category_items: list[ProfileCategory] = []
        raw_categories = data.get("categories")
        if isinstance(raw_categories, list):
            for item in raw_categories:
                if isinstance(item, dict):
                    category_items.append(ProfileCategory.from_dict(item))
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            theorem_name=(
                str(data["theorem_name"]) if data.get("theorem_name") is not None else None
            ),
            total_ms=(float(data["total_ms"]) if data.get("total_ms") is not None else None),
            lines=tuple(line_items),
            count=to_int(data.get("count"), default=len(line_items)) or len(line_items),
            categories=tuple(category_items),
            category_count=(
                to_int(data.get("category_count"), default=len(category_items))
                or len(category_items)
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "theorem_name": self.theorem_name,
            "total_ms": self.total_ms,
            "lines": [item.to_dict() for item in self.lines],
            "count": self.count,
            "categories": [item.to_dict() for item in self.categories],
            "category_count": self.category_count,
        }
