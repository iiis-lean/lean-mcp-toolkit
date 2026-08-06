"""Contracts for declaration soundness tools."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool


@dataclass(frozen=True)
class DeclarationSoundnessTarget(DictModel):
    file_path: str = ""
    declaration_name: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationSoundnessTarget":
        return cls(
            file_path=str(data.get("file_path") or ""),
            declaration_name=str(data.get("declaration_name") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "file_path": self.file_path,
            "declaration_name": self.declaration_name,
        }


@dataclass(frozen=True)
class SourceWarning(DictModel):
    line: int
    pattern: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SourceWarning":
        return cls(
            line=int(data.get("line") or 0),
            pattern=str(data.get("pattern") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "line": self.line,
            "pattern": self.pattern,
        }


@dataclass(frozen=True)
class DeclarationSoundnessResult(DictModel):
    file_path: str
    declaration_name: str
    success: bool
    error_message: str | None = None
    axioms: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[SourceWarning, ...] = field(default_factory=tuple)
    axiom_count: int = 0
    warning_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationSoundnessResult":
        raw_axioms = data.get("axioms")
        axioms = (
            tuple(str(item) for item in raw_axioms)
            if isinstance(raw_axioms, list)
            else tuple()
        )
        raw_warnings = data.get("warnings")
        warnings = (
            tuple(
                SourceWarning.from_dict(item)
                for item in raw_warnings
                if isinstance(item, dict)
            )
            if isinstance(raw_warnings, list)
            else tuple()
        )
        return cls(
            file_path=str(data.get("file_path") or ""),
            declaration_name=str(data.get("declaration_name") or ""),
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"])
                if data.get("error_message") is not None
                else None
            ),
            axioms=axioms,
            warnings=warnings,
            axiom_count=int(data.get("axiom_count") or len(axioms)),
            warning_count=int(data.get("warning_count") or len(warnings)),
        )

    def to_dict(self) -> JsonDict:
        return {
            "file_path": self.file_path,
            "declaration_name": self.declaration_name,
            "success": self.success,
            "error_message": self.error_message,
            "axioms": list(self.axioms),
            "warnings": [item.to_dict() for item in self.warnings],
            "axiom_count": self.axiom_count,
            "warning_count": self.warning_count,
        }


@dataclass(frozen=True)
class LspDeclarationSoundnessRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    declaration_name: str = ""
    scan_source: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationSoundnessRequest":
        scan_source = (
            to_bool(data.get("scan_source"), default=True)
            if "scan_source" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"])
                if data.get("project_root") is not None
                else None
            ),
            file_path=str(data.get("file_path") or ""),
            declaration_name=str(data.get("declaration_name") or ""),
            scan_source=scan_source,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "declaration_name": self.declaration_name,
            "scan_source": self.scan_source,
        }


@dataclass(frozen=True)
class LspDeclarationSoundnessResponse(DeclarationSoundnessResult):
    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationSoundnessResponse":
        parsed = DeclarationSoundnessResult.from_dict(data)
        return cls(**parsed.__dict__)


@dataclass(frozen=True)
class LspDeclarationSoundnessBatchRequest(DictModel):
    project_root: str | None = None
    declarations: tuple[DeclarationSoundnessTarget, ...] = field(default_factory=tuple)
    scan_source: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationSoundnessBatchRequest":
        raw_declarations = data.get("declarations")
        declarations: tuple[DeclarationSoundnessTarget, ...] = tuple()
        if isinstance(raw_declarations, list):
            if any(not isinstance(item, dict) for item in raw_declarations):
                raise ValueError("declarations items must be objects")
            declarations = tuple(
                DeclarationSoundnessTarget.from_dict(item) for item in raw_declarations
            )
        scan_source = (
            to_bool(data.get("scan_source"), default=True)
            if "scan_source" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"])
                if data.get("project_root") is not None
                else None
            ),
            declarations=declarations,
            scan_source=scan_source,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "declarations": [item.to_dict() for item in self.declarations],
            "scan_source": self.scan_source,
        }


@dataclass(frozen=True)
class LspDeclarationSoundnessBatchResponse(DictModel):
    success: bool
    error_message: str | None = None
    items: tuple[DeclarationSoundnessResult, ...] = field(default_factory=tuple)
    count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspDeclarationSoundnessBatchResponse":
        raw_items = data.get("items")
        items = (
            tuple(
                DeclarationSoundnessResult.from_dict(item)
                for item in raw_items
                if isinstance(item, dict)
            )
            if isinstance(raw_items, list)
            else tuple()
        )
        success_count = sum(item.success for item in items)
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"])
                if data.get("error_message") is not None
                else None
            ),
            items=items,
            count=int(data.get("count") or len(items)),
            success_count=int(data.get("success_count") or success_count),
            failure_count=int(
                data.get("failure_count") or (len(items) - success_count)
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }
