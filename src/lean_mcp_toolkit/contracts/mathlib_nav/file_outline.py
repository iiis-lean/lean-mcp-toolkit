"""Contracts for mathlib_nav.file_outline."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict
from ..search_nav import (
    RepoNavDeclarationItem,
    RepoNavFileOutlineResponse,
    RepoNavOutlineSummary,
    RepoNavScopeCmdItem,
    RepoNavSectionItem,
    RepoNavTarget,
)
from ..search_nav.common import parse_int_or_none, to_opt_str


@dataclass(slots=True, frozen=True)
class MathlibNavFileOutlineRequest(DictModel):
    project_root: str | None = None
    mathlib_root: str | None = None
    target: str = ""
    include_imports: bool | None = None
    include_module_doc: bool | None = None
    include_section_doc: bool | None = None
    include_decl_headers: bool | None = None
    include_scope_cmds: bool | None = None
    limit_decls: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibNavFileOutlineRequest":
        return cls(
            project_root=to_opt_str(data, "project_root"),
            mathlib_root=to_opt_str(data, "mathlib_root"),
            target=str(data.get("target") or ""),
            include_imports=(bool(data["include_imports"]) if "include_imports" in data else None),
            include_module_doc=(
                bool(data["include_module_doc"]) if "include_module_doc" in data else None
            ),
            include_section_doc=(
                bool(data["include_section_doc"]) if "include_section_doc" in data else None
            ),
            include_decl_headers=(
                bool(data["include_decl_headers"]) if "include_decl_headers" in data else None
            ),
            include_scope_cmds=(
                bool(data["include_scope_cmds"]) if "include_scope_cmds" in data else None
            ),
            limit_decls=parse_int_or_none(data.get("limit_decls")),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "mathlib_root": self.mathlib_root,
            "target": self.target,
            "include_imports": self.include_imports,
            "include_module_doc": self.include_module_doc,
            "include_section_doc": self.include_section_doc,
            "include_decl_headers": self.include_decl_headers,
            "include_scope_cmds": self.include_scope_cmds,
            "limit_decls": self.limit_decls,
        }


MathlibNavTarget = RepoNavTarget
MathlibNavSectionItem = RepoNavSectionItem
MathlibNavDeclarationItem = RepoNavDeclarationItem
MathlibNavScopeCmdItem = RepoNavScopeCmdItem
MathlibNavOutlineSummary = RepoNavOutlineSummary
MathlibNavFileOutlineResponse = RepoNavFileOutlineResponse


__all__ = [
    "MathlibNavFileOutlineRequest",
    "MathlibNavTarget",
    "MathlibNavSectionItem",
    "MathlibNavDeclarationItem",
    "MathlibNavScopeCmdItem",
    "MathlibNavOutlineSummary",
    "MathlibNavFileOutlineResponse",
]
