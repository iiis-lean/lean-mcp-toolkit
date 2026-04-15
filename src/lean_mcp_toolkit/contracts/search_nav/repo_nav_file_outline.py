"""Contracts for repo_nav.file_outline."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool
from .common import parse_limit, to_opt_str


@dataclass(frozen=True)
class RepoNavFileOutlineRequest(DictModel):
    repo_root: str | None = None
    target: str = ""
    include_imports: bool | None = None
    include_module_doc: bool | None = None
    include_section_doc: bool | None = None
    include_decl_headers: bool | None = None
    include_scope_cmds: bool | None = None
    limit_decls: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavFileOutlineRequest":
        return cls(
            repo_root=to_opt_str(data, "repo_root"),
            target=str(data.get("target") or ""),
            include_imports=(
                to_bool(data.get("include_imports"), default=True)
                if "include_imports" in data
                else None
            ),
            include_module_doc=(
                to_bool(data.get("include_module_doc"), default=True)
                if "include_module_doc" in data
                else None
            ),
            include_section_doc=(
                to_bool(data.get("include_section_doc"), default=True)
                if "include_section_doc" in data
                else None
            ),
            include_decl_headers=(
                to_bool(data.get("include_decl_headers"), default=True)
                if "include_decl_headers" in data
                else None
            ),
            include_scope_cmds=(
                to_bool(data.get("include_scope_cmds"), default=True)
                if "include_scope_cmds" in data
                else None
            ),
            limit_decls=parse_limit(data.get("limit_decls"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "repo_root": self.repo_root,
            "target": self.target,
            "include_imports": self.include_imports,
            "include_module_doc": self.include_module_doc,
            "include_section_doc": self.include_section_doc,
            "include_decl_headers": self.include_decl_headers,
            "include_scope_cmds": self.include_scope_cmds,
            "limit_decls": self.limit_decls,
        }


@dataclass(frozen=True)
class RepoNavTarget(DictModel):
    file_path: str
    module_path: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavTarget":
        return cls(
            file_path=str(data.get("file_path") or ""),
            module_path=to_opt_str(data, "module_path"),
        )


@dataclass(frozen=True)
class RepoNavSectionItem(DictModel):
    title: str
    line_start: int
    line_end: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavSectionItem":
        return cls(
            title=str(data.get("title") or ""),
            line_start=int(data.get("line_start") or 0),
            line_end=(int(data["line_end"]) if data.get("line_end") is not None else None),
        )


@dataclass(frozen=True)
class RepoNavDeclarationItem(DictModel):
    decl_kind: str
    full_name: str | None
    line_start: int
    line_end: int | None = None
    header_preview: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavDeclarationItem":
        return cls(
            decl_kind=str(data.get("decl_kind") or ""),
            full_name=to_opt_str(data, "full_name"),
            line_start=int(data.get("line_start") or 0),
            line_end=(int(data["line_end"]) if data.get("line_end") is not None else None),
            header_preview=to_opt_str(data, "header_preview"),
        )


@dataclass(frozen=True)
class RepoNavScopeCmdItem(DictModel):
    kind: str
    target: str | None
    line_start: int
    line_end: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavScopeCmdItem":
        return cls(
            kind=str(data.get("kind") or ""),
            target=to_opt_str(data, "target"),
            line_start=int(data.get("line_start") or 0),
            line_end=(int(data["line_end"]) if data.get("line_end") is not None else None),
        )


@dataclass(frozen=True)
class RepoNavOutlineSummary(DictModel):
    total_lines: int
    decl_count: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavOutlineSummary":
        return cls(
            total_lines=int(data.get("total_lines") or 0),
            decl_count=int(data.get("decl_count") or 0),
        )


@dataclass(frozen=True)
class RepoNavFileOutlineResponse(DictModel):
    success: bool
    error_message: str | None = None
    target: RepoNavTarget | None = None
    imports: tuple[str, ...] = field(default_factory=tuple)
    module_doc: str | None = None
    sections: tuple[RepoNavSectionItem, ...] = field(default_factory=tuple)
    declarations: tuple[RepoNavDeclarationItem, ...] = field(default_factory=tuple)
    scope_cmds: tuple[RepoNavScopeCmdItem, ...] = field(default_factory=tuple)
    summary: RepoNavOutlineSummary | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RepoNavFileOutlineResponse":
        raw_sections = data.get("sections")
        sections: list[RepoNavSectionItem] = []
        if isinstance(raw_sections, list):
            for item in raw_sections:
                if isinstance(item, dict):
                    sections.append(RepoNavSectionItem.from_dict(item))

        raw_decls = data.get("declarations")
        decls: list[RepoNavDeclarationItem] = []
        if isinstance(raw_decls, list):
            for item in raw_decls:
                if isinstance(item, dict):
                    decls.append(RepoNavDeclarationItem.from_dict(item))

        raw_scope_cmds = data.get("scope_cmds")
        scope_cmds: list[RepoNavScopeCmdItem] = []
        if isinstance(raw_scope_cmds, list):
            for item in raw_scope_cmds:
                if isinstance(item, dict):
                    scope_cmds.append(RepoNavScopeCmdItem.from_dict(item))

        raw_imports = data.get("imports")
        imports: list[str] = []
        if isinstance(raw_imports, list):
            for item in raw_imports:
                if item is not None:
                    imports.append(str(item))

        target_raw = data.get("target")
        summary_raw = data.get("summary")

        return cls(
            success=to_bool(data.get("success"), default=False),
            error_message=to_opt_str(data, "error_message"),
            target=RepoNavTarget.from_dict(target_raw) if isinstance(target_raw, dict) else None,
            imports=tuple(imports),
            module_doc=to_opt_str(data, "module_doc"),
            sections=tuple(sections),
            declarations=tuple(decls),
            scope_cmds=tuple(scope_cmds),
            summary=(
                RepoNavOutlineSummary.from_dict(summary_raw)
                if isinstance(summary_raw, dict)
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "target": self.target.to_dict() if self.target else None,
            "imports": list(self.imports),
            "module_doc": self.module_doc,
            "sections": [item.to_dict() for item in self.sections],
            "declarations": [item.to_dict() for item in self.declarations],
            "scope_cmds": [item.to_dict() for item in self.scope_cmds],
            "summary": self.summary.to_dict() if self.summary else None,
        }


__all__ = [
    "RepoNavFileOutlineRequest",
    "RepoNavTarget",
    "RepoNavSectionItem",
    "RepoNavDeclarationItem",
    "RepoNavScopeCmdItem",
    "RepoNavOutlineSummary",
    "RepoNavFileOutlineResponse",
]
