"""LeanExplore backend selection wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...config import LeanExploreBackendConfig, SearchCoreConfig
from .api_backend import LeanExploreApiBackend
from .base import LeanExploreBackend, LeanExploreRecord, LeanExploreSearchResult
from .local_backend import LeanExploreLocalBackend


@dataclass(slots=True)
class LeanExploreBackendAdapter(LeanExploreBackend):
    backend_config: LeanExploreBackendConfig
    search_config: SearchCoreConfig
    _backend: LeanExploreBackend | None = field(default=None, init=False, repr=False)

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        return self._get_backend().search(
            query=query,
            limit=limit,
            rerank_top=rerank_top,
            packages=packages,
        )

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        return self._get_backend().get_by_id(declaration_id)

    def _get_backend(self) -> LeanExploreBackend:
        if self._backend is not None:
            return self._backend

        mode = self.backend_config.mode.strip().lower()
        if mode == "api":
            self._backend = LeanExploreApiBackend(backend_config=self.backend_config)
        else:
            self._backend = LeanExploreLocalBackend(
                backend_config=self.backend_config,
                search_config=self.search_config,
            )
        return self._backend


__all__ = ["LeanExploreBackendAdapter"]
