"""mathlib_nav service implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from ...backends.lean.path import resolve_project_root
from ...config import ToolkitConfig
from ...contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavFileOutlineResponse,
    MathlibNavGrepRequest,
    MathlibNavGrepResponse,
    MathlibNavReadRequest,
    MathlibNavReadResponse,
    MathlibNavTreeRequest,
    MathlibNavTreeResponse,
)
from ...contracts.search_nav import (
    RepoNavFileOutlineRequest,
    RepoNavGrepRequest,
    RepoNavReadRequest,
    RepoNavTreeRequest,
)
from ...core.services import MathlibNavService
from ..search_nav.service_impl import SearchNavServiceImpl


@dataclass(slots=True)
class MathlibNavServiceImpl(MathlibNavService):
    config: ToolkitConfig
    repo_nav_service: SearchNavServiceImpl = field(init=False)

    def __post_init__(self) -> None:
        self.repo_nav_service = SearchNavServiceImpl(config=self.config)

    def run_mathlib_nav_tree(self, req: MathlibNavTreeRequest) -> MathlibNavTreeResponse:
        try:
            mathlib_root = self._resolve_mathlib_root(
                project_root=req.project_root,
                mathlib_root=req.mathlib_root,
            )
            inner_req = RepoNavTreeRequest(
                repo_root=str(mathlib_root),
                base=self._normalize_mathlib_locator(req.base, allow_empty=True),
                depth=req.depth,
                name_filter=req.name_filter,
                limit=req.limit,
                offset=req.offset,
            )
            return self.repo_nav_service.run_repo_nav_tree(inner_req)
        except Exception as exc:
            return MathlibNavTreeResponse(success=False, error_message=str(exc))

    def run_mathlib_nav_file_outline(
        self,
        req: MathlibNavFileOutlineRequest,
    ) -> MathlibNavFileOutlineResponse:
        try:
            mathlib_root = self._resolve_mathlib_root(
                project_root=req.project_root,
                mathlib_root=req.mathlib_root,
            )
            inner_req = RepoNavFileOutlineRequest(
                repo_root=str(mathlib_root),
                target=self._normalize_mathlib_locator(req.target, allow_empty=False),
                include_imports=req.include_imports,
                include_module_doc=req.include_module_doc,
                include_section_doc=req.include_section_doc,
                include_decl_headers=req.include_decl_headers,
                include_scope_cmds=req.include_scope_cmds,
                limit_decls=req.limit_decls,
            )
            return self.repo_nav_service.run_repo_nav_file_outline(inner_req)
        except Exception as exc:
            return MathlibNavFileOutlineResponse(success=False, error_message=str(exc))

    def run_mathlib_nav_grep(self, req: MathlibNavGrepRequest) -> MathlibNavGrepResponse:
        try:
            mathlib_root = self._resolve_mathlib_root(
                project_root=req.project_root,
                mathlib_root=req.mathlib_root,
            )
            base = (req.base or "").strip()
            target = (req.target or "").strip()
            if base and target:
                raise ValueError("base and target are mutually exclusive")

            path_filter = None
            if target:
                path_filter = self._mathlib_target_to_path_filter(target)
            elif base:
                path_filter = self._mathlib_base_to_path_filter(base)

            inner_req = RepoNavGrepRequest(
                repo_root=str(mathlib_root),
                query=req.query,
                match_mode=req.match_mode,
                path_filter=path_filter,
                include_deps=False,
                limit=req.limit,
                context_lines=req.context_lines,
                scopes=req.scopes,
            )
            return self.repo_nav_service.run_repo_nav_grep(inner_req)
        except Exception as exc:
            return MathlibNavGrepResponse(success=False, error_message=str(exc), query=req.query)

    def run_mathlib_nav_read(self, req: MathlibNavReadRequest) -> MathlibNavReadResponse:
        try:
            mathlib_root = self._resolve_mathlib_root(
                project_root=req.project_root,
                mathlib_root=req.mathlib_root,
            )
            inner_req = RepoNavReadRequest(
                repo_root=str(mathlib_root),
                target=self._normalize_mathlib_locator(req.target, allow_empty=False),
                start_line=req.start_line,
                end_line=req.end_line,
                max_lines=req.max_lines,
                with_line_numbers=req.with_line_numbers,
            )
            return self.repo_nav_service.run_repo_nav_read(inner_req)
        except Exception as exc:
            return MathlibNavReadResponse(success=False, error_message=str(exc))

    def _resolve_mathlib_root(self, *, project_root: str | None, mathlib_root: str | None) -> Path:
        if mathlib_root is not None and mathlib_root.strip():
            raw = Path(mathlib_root).expanduser().resolve()
            if not raw.exists() or not raw.is_dir():
                raise FileNotFoundError(f"mathlib_root is not a directory: {raw}")
            if raw.name == "Mathlib":
                return raw
            nested = raw / "Mathlib"
            if nested.exists() and nested.is_dir():
                return nested.resolve()
            raise FileNotFoundError(
                f"mathlib_root must be Mathlib directory or contain Mathlib/: {raw}"
            )

        raw_project = (
            (project_root or "").strip()
            or (self.config.server.default_project_root or "").strip()
            or os.getcwd()
        )
        project = resolve_project_root(
            raw_project,
            default_project_root=self.config.server.default_project_root,
            allow_cwd_fallback=True,
        )

        candidates = (
            project / ".lake" / "packages" / "mathlib" / "Mathlib",
            project / "Mathlib",
            project if project.name == "Mathlib" else None,
        )
        for candidate in candidates:
            if candidate is None:
                continue
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()

        raise FileNotFoundError(
            f"cannot locate Mathlib source root under project_root={project}; "
            "tried .lake/packages/mathlib/Mathlib and project_root/Mathlib"
        )

    @staticmethod
    def _normalize_mathlib_locator(raw: str | None, *, allow_empty: bool) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None if allow_empty else text

        if text == "Mathlib":
            return None if allow_empty else text
        if text.startswith("Mathlib."):
            return text[len("Mathlib.") :]
        if text.startswith("Mathlib/"):
            return text[len("Mathlib/") :]
        if text.startswith("Mathlib\\"):
            return text[len("Mathlib\\") :]
        return text

    def _mathlib_base_to_path_filter(self, raw: str) -> str:
        locator = self._normalize_mathlib_locator(raw, allow_empty=False)
        if locator is None:
            raise ValueError("base must not be empty")
        return self._locator_to_path_prefix(locator)

    def _mathlib_target_to_path_filter(self, raw: str) -> str:
        locator = self._normalize_mathlib_locator(raw, allow_empty=False)
        if locator is None:
            raise ValueError("target must not be empty")
        if "/" in locator or "\\" in locator:
            normalized = locator.replace("\\", "/")
            return normalized if normalized.endswith(".lean") else f"{normalized}.lean"
        return f"{locator.replace('.', '/')}.lean"

    @staticmethod
    def _locator_to_path_prefix(locator: str) -> str:
        normalized = locator.replace("\\", "/").strip("/")
        if "/" not in normalized and normalized.endswith(".lean"):
            return normalized
        if "/" in normalized:
            return normalized
        return normalized.replace(".", "/")


__all__ = ["MathlibNavServiceImpl"]
