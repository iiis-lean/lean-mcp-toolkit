"""Contracts for lsp.file_outline."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int
from .common import OutlineEntry


@dataclass(slots=True, frozen=True)
class LspFileOutlineRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    max_declarations: int | None = None
    response_format: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspFileOutlineRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            max_declarations=to_int(data.get("max_declarations"), default=None),
            response_format=(
                str(data["response_format"]) if data.get("response_format") is not None else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "max_declarations": self.max_declarations,
            "response_format": self.response_format,
        }


@dataclass(slots=True, frozen=True)
class LspFileOutlineResponse(DictModel):
    success: bool
    error_message: str | None = None
    imports: tuple[str, ...] = field(default_factory=tuple)
    declarations: tuple[OutlineEntry, ...] = field(default_factory=tuple)
    total_declarations: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspFileOutlineResponse":
        parsed: list[OutlineEntry] = []
        raw_decls = data.get("declarations")
        if isinstance(raw_decls, list):
            for item in raw_decls:
                if isinstance(item, dict):
                    parsed.append(OutlineEntry.from_dict(item))
        raw_imports = data.get("imports")
        imports: list[str] = []
        if isinstance(raw_imports, list):
            imports = [str(item) for item in raw_imports]
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            imports=tuple(imports),
            declarations=tuple(parsed),
            total_declarations=to_int(data.get("total_declarations"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "imports": list(self.imports),
            "declarations": [item.to_dict() for item in self.declarations],
            "total_declarations": self.total_declarations,
        }
