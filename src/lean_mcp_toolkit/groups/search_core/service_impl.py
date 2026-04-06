"""search_core service implementation.

This group adapts declaration search functionality from the external
``lean-explore`` project into the toolkit's local/http/MCP tool surface.

Reference project:
- lean-explore: https://github.com/justincasher/lean-explore
"""

from __future__ import annotations

from dataclasses import dataclass

from ...backends.lean_explore import LeanExploreBackend, LeanExploreBackendAdapter
from ...config import ToolkitConfig
from ...contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclFindResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
    MathlibDeclSummaryItem,
)
from ...core.services import SearchCoreService


@dataclass(slots=True)
class SearchCoreServiceImpl(SearchCoreService):
    """Service wrapper around ``lean-explore`` search/get capabilities."""

    config: ToolkitConfig
    lean_explore_backend: LeanExploreBackend

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        lean_explore_backend: LeanExploreBackend | None = None,
    ):
        self.config = config
        self.lean_explore_backend = lean_explore_backend or LeanExploreBackendAdapter(
            backend_config=config.backends.lean_explore,
            search_config=config.search_core,
        )

    def run_mathlib_decl_find(
        self,
        req: MathlibDeclFindRequest,
    ) -> MathlibDeclFindResponse:
        """Adapt the lean-explore search endpoint to the toolkit contract."""
        query = req.query.strip()
        if not query:
            return MathlibDeclFindResponse(
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

        try:
            result = self.lean_explore_backend.search(
                query=query,
                limit=max(1, int(limit)),
                rerank_top=rerank_top,
                packages=tuple(packages) if packages is not None else None,
            )
        except Exception:
            self._recycle_backend_best_effort()
            raise

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

        return MathlibDeclFindResponse(
            query=result.query,
            count=len(items),
            processing_time_ms=result.processing_time_ms,
            results=items,
        )

    def run_mathlib_decl_get(self, req: MathlibDeclGetRequest) -> MathlibDeclGetResponse:
        """Adapt the lean-explore get-by-id endpoint to the toolkit contract."""
        declaration_id = int(req.declaration_id)
        if declaration_id <= 0:
            return MathlibDeclGetResponse(found=False, item=None)

        try:
            item = self.lean_explore_backend.get_by_id(declaration_id)
        except Exception:
            self._recycle_backend_best_effort()
            raise
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

    def close(self) -> None:
        close = getattr(self.lean_explore_backend, "close", None)
        if callable(close):
            close()

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

    def _recycle_backend_best_effort(self) -> None:
        recycle = getattr(self.lean_explore_backend, "recycle", None)
        if callable(recycle):
            try:
                recycle()
            except Exception:
                pass


__all__ = ["SearchCoreServiceImpl"]
