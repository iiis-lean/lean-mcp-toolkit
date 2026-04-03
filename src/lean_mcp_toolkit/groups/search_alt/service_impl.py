"""search_alt service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...backends.lean.path import resolve_project_root
from ...backends.search_providers import SearchAltBackendManager
from ...config import ToolkitConfig
from ...contracts.search_alt import (
    LeanDexItem,
    LeanFinderItem,
    LeanSearchItem,
    LoogleItem,
    SearchAltLeanDexRequest,
    SearchAltLeanDexResponse,
    SearchAltLeanFinderRequest,
    SearchAltLeanFinderResponse,
    SearchAltLeanSearchRequest,
    SearchAltLeanSearchResponse,
    SearchAltLoogleRequest,
    SearchAltLoogleResponse,
)
from ...core.services import SearchAltService


@dataclass(slots=True)
class SearchAltServiceImpl(SearchAltService):
    config: ToolkitConfig
    backend_manager: SearchAltBackendManager

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        backend_manager: SearchAltBackendManager | None = None,
    ):
        self.config = config
        self.backend_manager = backend_manager or SearchAltBackendManager(
            config=config.backends.search_providers
        )

    def run_leansearch(self, req: SearchAltLeanSearchRequest) -> SearchAltLeanSearchResponse:
        try:
            query = req.query.strip()
            if not query:
                raise ValueError("query is required")
            include_raw = self.config.search_alt.include_raw_payload_default
            limit = self._cap(
                req.num_results or self.config.search_alt.leansearch_default_num_results,
                self.backend_manager.config.leansearch.max_results_hard_limit,
            )
            items = tuple(
                LeanSearchItem.from_dict(item)
                for item in self.backend_manager.leansearch.search(
                    query=query,
                    num_results=limit,
                    include_raw_payload=include_raw,
                )
            )
            return SearchAltLeanSearchResponse(
                success=True,
                error_message=None,
                query=query,
                provider="leansearch",
                backend_mode="remote",
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return SearchAltLeanSearchResponse(
                success=False,
                error_message=str(exc),
                query=req.query,
                provider="leansearch",
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    def run_leandex(self, req: SearchAltLeanDexRequest) -> SearchAltLeanDexResponse:
        try:
            query = req.query.strip()
            if not query:
                raise ValueError("query is required")
            include_raw = self.config.search_alt.include_raw_payload_default
            limit = self._cap(
                req.num_results or self.config.search_alt.leandex_default_num_results,
                self.backend_manager.config.leandex.max_results_hard_limit,
            )
            items = tuple(
                LeanDexItem.from_dict(item)
                for item in self.backend_manager.leandex.search(
                    query=query,
                    num_results=limit,
                    include_raw_payload=include_raw,
                )
            )
            return SearchAltLeanDexResponse(
                success=True,
                error_message=None,
                query=query,
                provider="leandex",
                backend_mode="remote",
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return SearchAltLeanDexResponse(
                success=False,
                error_message=str(exc),
                query=req.query,
                provider="leandex",
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    def run_loogle(self, req: SearchAltLoogleRequest) -> SearchAltLoogleResponse:
        try:
            query = req.query.strip()
            if not query:
                raise ValueError("query is required")
            include_raw = self.config.search_alt.include_raw_payload_default
            limit = self._cap(
                req.num_results or self.config.search_alt.loogle_default_num_results,
                self.backend_manager.config.loogle.max_results_hard_limit,
            )
            backend_mode, raw_items = self.backend_manager.search_loogle(
                query=query,
                num_results=limit,
                include_raw_payload=include_raw,
                project_root=self._default_project_root(),
            )
            items = tuple(LoogleItem.from_dict(item) for item in raw_items)
            return SearchAltLoogleResponse(
                success=True,
                error_message=None,
                query=query,
                provider="loogle",
                backend_mode=backend_mode,
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return SearchAltLoogleResponse(
                success=False,
                error_message=str(exc),
                query=req.query,
                provider="loogle",
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    def run_leanfinder(self, req: SearchAltLeanFinderRequest) -> SearchAltLeanFinderResponse:
        try:
            query = req.query.strip()
            if not query:
                raise ValueError("query is required")
            include_raw = self.config.search_alt.include_raw_payload_default
            limit = self._cap(
                req.num_results or self.config.search_alt.leanfinder_default_num_results,
                self.backend_manager.config.leanfinder.max_results_hard_limit,
            )
            items = tuple(
                LeanFinderItem.from_dict(item)
                for item in self.backend_manager.leanfinder.search(
                    query=query,
                    num_results=limit,
                    include_raw_payload=include_raw,
                )
            )
            return SearchAltLeanFinderResponse(
                success=True,
                error_message=None,
                query=query,
                provider="leanfinder",
                backend_mode="remote",
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return SearchAltLeanFinderResponse(
                success=False,
                error_message=str(exc),
                query=req.query,
                provider="leanfinder",
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    @staticmethod
    def _cap(value: int, hard_limit: int) -> int:
        return max(1, min(value, hard_limit))

    def _default_project_root(self) -> Path | None:
        root = self.config.server.default_project_root
        if not root:
            return None
        try:
            return resolve_project_root(
                root,
                default_project_root=None,
                allow_cwd_fallback=False,
            )
        except Exception:
            return None
