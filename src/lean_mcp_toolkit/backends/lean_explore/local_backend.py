"""Local lean-explore backend adapter.

This module embeds the external ``lean-explore`` Python package directly:
https://github.com/justincasher/lean-explore
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ...config import LeanExploreBackendConfig, SearchCoreConfig
from .base import LeanExploreRecord, LeanExploreSearchResult, run_async
from .version_map import resolve_toolchain_id


@dataclass(slots=True)
class LeanExploreLocalBackend:
    """Adapter around the local lean-explore ``SearchEngine`` + ``Service``."""

    backend_config: LeanExploreBackendConfig
    search_config: SearchCoreConfig
    _service: Any | None = field(default=None, init=False, repr=False)

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        service = self._get_service()
        response = run_async(
            service.search(
                query=query,
                limit=limit,
                rerank_top=rerank_top,
                packages=list(packages) if packages is not None else None,
            )
        )
        items = tuple(self._to_record(item) for item in getattr(response, "results", []))
        return LeanExploreSearchResult(
            query=str(getattr(response, "query", query) or query),
            processing_time_ms=(
                int(getattr(response, "processing_time_ms"))
                if getattr(response, "processing_time_ms", None) is not None
                else None
            ),
            items=items,
        )

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        service = self._get_service()
        item = run_async(service.get_by_id(int(declaration_id)))
        if item is None:
            return None
        return self._to_record(item)

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service

        self._configure_env()
        try:
            from lean_explore.search.engine import SearchEngine
            from lean_explore.search.service import Service
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(
                "lean_explore local backend is unavailable; install lean_explore package"
            ) from exc

        try:
            engine = SearchEngine()
            service = Service(engine=engine)
        except Exception as exc:
            raise RuntimeError(f"failed to initialize lean_explore local backend: {exc}") from exc

        if self.search_config.require_mathlib or self.backend_config.startup_verify_mathlib:
            probe = run_async(
                service.search(
                    query="Nat.succ",
                    limit=1,
                    rerank_top=0,
                    packages=["Mathlib"],
                )
            )
            if len(getattr(probe, "results", [])) == 0:
                raise RuntimeError(
                    "lean_explore local backend initialized but Mathlib index probe returned empty"
                )

        self._service = service
        return self._service

    def _configure_env(self) -> None:
        toolchain_id = resolve_toolchain_id(self.search_config.mathlib_lean_version)
        os.environ["LEAN_EXPLORE_VERSION"] = toolchain_id
        if self.backend_config.cache_dir:
            os.environ["LEAN_EXPLORE_CACHE_DIR"] = self.backend_config.cache_dir
        if self.backend_config.data_dir:
            os.environ["LEAN_EXPLORE_DATA_DIR"] = self.backend_config.data_dir
        if self.backend_config.packages_root:
            os.environ["LEAN_EXPLORE_PACKAGES_ROOT"] = self.backend_config.packages_root

    @staticmethod
    def _to_record(item: Any) -> LeanExploreRecord:
        return LeanExploreRecord(
            id=int(getattr(item, "id", 0)),
            name=str(getattr(item, "name", "") or ""),
            module=(
                str(getattr(item, "module"))
                if getattr(item, "module", None) is not None
                else None
            ),
            docstring=(
                str(getattr(item, "docstring"))
                if getattr(item, "docstring", None) is not None
                else None
            ),
            source_text=(
                str(getattr(item, "source_text"))
                if getattr(item, "source_text", None) is not None
                else None
            ),
            source_link=(
                str(getattr(item, "source_link"))
                if getattr(item, "source_link", None) is not None
                else None
            ),
            dependencies=(
                str(getattr(item, "dependencies"))
                if getattr(item, "dependencies", None) is not None
                else None
            ),
            informalization=(
                str(getattr(item, "informalization"))
                if getattr(item, "informalization", None) is not None
                else None
            ),
        )


__all__ = ["LeanExploreLocalBackend"]
