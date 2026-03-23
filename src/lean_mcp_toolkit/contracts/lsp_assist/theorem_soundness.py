"""Contracts for lsp.theorem_soundness."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool


@dataclass(slots=True, frozen=True)
class LspTheoremSoundnessRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    theorem_name: str = ""
    scan_source: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspTheoremSoundnessRequest":
        scan_source = (
            to_bool(data.get("scan_source"), default=True)
            if "scan_source" in data
            else None
        )
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            theorem_name=str(data.get("theorem_name") or ""),
            scan_source=scan_source,
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "theorem_name": self.theorem_name,
            "scan_source": self.scan_source,
        }


@dataclass(slots=True, frozen=True)
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


@dataclass(slots=True, frozen=True)
class LspTheoremSoundnessResponse(DictModel):
    success: bool
    error_message: str | None = None
    axioms: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[SourceWarning, ...] = field(default_factory=tuple)
    axiom_count: int = 0
    warning_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspTheoremSoundnessResponse":
        raw_axioms = data.get("axioms")
        axioms: list[str] = []
        if isinstance(raw_axioms, list):
            axioms = [str(item) for item in raw_axioms]

        warnings: list[SourceWarning] = []
        raw_warnings = data.get("warnings")
        if isinstance(raw_warnings, list):
            for item in raw_warnings:
                if isinstance(item, dict):
                    warnings.append(SourceWarning.from_dict(item))

        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            axioms=tuple(axioms),
            warnings=tuple(warnings),
            axiom_count=int(data.get("axiom_count") or len(axioms)),
            warning_count=int(data.get("warning_count") or len(warnings)),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "axioms": list(self.axioms),
            "warnings": [item.to_dict() for item in self.warnings],
            "axiom_count": self.axiom_count,
            "warning_count": self.warning_count,
        }

