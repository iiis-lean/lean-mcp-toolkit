"""search_core service implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from ...backends.lean_explore import LeanExploreBackend, LeanExploreBackendAdapter
from ...config import ToolkitConfig
from ...contracts.search_core import (
    LocalDeclSearchRequest,
    LocalDeclSearchResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
    MathlibDeclSearchRequest,
    MathlibDeclSearchResponse,
    MathlibDeclSummaryItem,
)
from ...core.services import SearchCoreService
from .local_decl_search import LocalDeclSearcher


@dataclass(slots=True)
class SearchCoreServiceImpl(SearchCoreService):
    config: ToolkitConfig
    lean_explore_backend: LeanExploreBackend
    local_decl_searcher: LocalDeclSearcher = field(default_factory=LocalDeclSearcher)

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        lean_explore_backend: LeanExploreBackend | None = None,
        local_decl_searcher: LocalDeclSearcher | None = None,
    ):
        self.config = config
        self.lean_explore_backend = lean_explore_backend or LeanExploreBackendAdapter(
            backend_config=config.backends.lean_explore,
            search_config=config.search_core,
        )
        self.local_decl_searcher = local_decl_searcher or LocalDeclSearcher(
            local_decl_max_candidates=config.search_core.local_decl_max_candidates,
            local_decl_require_rg=config.search_core.local_decl_require_rg,
        )

    def run_mathlib_decl_search(
        self,
        req: MathlibDeclSearchRequest,
    ) -> MathlibDeclSearchResponse:
        query = req.query.strip()
        if not query:
            return MathlibDeclSearchResponse(
                query="",
                count=0,
                processing_time_ms=None,
                results=tuple(),
            )

        limit = req.limit or self.config.search_core.default_limit
        rerank_top = (
            req.rerank_top
            if req.rerank_top is not None
            else self.config.search_core.default_rerank_top
        )
        packages = (
            req.packages
            if req.packages is not None
            else self.config.search_core.default_packages
        )

        result = self.lean_explore_backend.search(
            query=query,
            limit=max(1, int(limit)),
            rerank_top=rerank_top,
            packages=tuple(packages) if packages is not None else None,
        )

        items = tuple(
            self._project_item(
                record=item,
                include_module=req.include_module,
                include_docstring=req.include_docstring,
                include_source_text=req.include_source_text,
                include_source_link=req.include_source_link,
                include_dependencies=req.include_dependencies,
                include_informalization=req.include_informalization,
            )
            for item in result.items
        )

        return MathlibDeclSearchResponse(
            query=result.query,
            count=len(items),
            processing_time_ms=result.processing_time_ms,
            results=items,
        )

    def run_mathlib_decl_get(self, req: MathlibDeclGetRequest) -> MathlibDeclGetResponse:
        declaration_id = int(req.declaration_id)
        if declaration_id <= 0:
            return MathlibDeclGetResponse(found=False, item=None)

        item = self.lean_explore_backend.get_by_id(declaration_id)
        if item is None:
            return MathlibDeclGetResponse(found=False, item=None)

        projected = self._project_item(
            record=item,
            include_module=req.include_module,
            include_docstring=req.include_docstring,
            include_source_text=req.include_source_text,
            include_source_link=req.include_source_link,
            include_dependencies=req.include_dependencies,
            include_informalization=req.include_informalization,
        )
        return MathlibDeclGetResponse(found=True, item=projected)

    def run_local_decl_search(self, req: LocalDeclSearchRequest) -> LocalDeclSearchResponse:
        query = req.query.strip()
        if not query:
            return LocalDeclSearchResponse(query="", count=0, items=tuple())

        project_root = self._resolve_project_root(req.project_root)
        limit = req.limit or self.config.search_core.local_decl_default_limit
        include_dependencies = (
            req.include_dependencies
            if req.include_dependencies is not None
            else self.config.search_core.local_decl_include_dependencies
        )
        include_stdlib = (
            req.include_stdlib
            if req.include_stdlib is not None
            else self.config.search_core.local_decl_include_stdlib
        )

        items = self.local_decl_searcher.search(
            project_root=project_root,
            query=query,
            limit=max(1, int(limit)),
            include_dependencies=bool(include_dependencies),
            include_stdlib=bool(include_stdlib),
        )
        return LocalDeclSearchResponse(query=query, count=len(items), items=items)

    def _resolve_project_root(self, project_root: str | None) -> Path:
        root = project_root or self.config.server.default_project_root or os.getcwd()
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"project_root is not a directory: {resolved}")
        return resolved

    @staticmethod
    def _project_item(
        *,
        record,
        include_module: bool,
        include_docstring: bool,
        include_source_text: bool,
        include_source_link: bool,
        include_dependencies: bool,
        include_informalization: bool,
    ) -> MathlibDeclSummaryItem:
        return MathlibDeclSummaryItem(
            id=record.id,
            name=record.name,
            module=record.module if include_module else None,
            docstring=record.docstring if include_docstring else None,
            source_text=record.source_text if include_source_text else None,
            source_link=record.source_link if include_source_link else None,
            dependencies=record.dependencies if include_dependencies else None,
            informalization=record.informalization if include_informalization else None,
        )


__all__ = ["SearchCoreServiceImpl"]
