"""Remote API lean-explore backend adapter.

This adapter talks to the external ``lean-explore`` API client:
https://github.com/justincasher/lean-explore
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ...config import LeanExploreBackendConfig
from .base import LeanExploreRecord, LeanExploreSearchResult, run_async


@dataclass(slots=True)
class LeanExploreApiBackend:
    """Adapter around the remote lean-explore API client."""

    backend_config: LeanExploreBackendConfig
    _client: Any | None = field(default=None, init=False, repr=False)

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        client = self._get_client()
        response = run_async(
            client.search(
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
        client = self._get_client()
        item = run_async(client.get_by_id(int(declaration_id)))
        if item is None:
            return None
        return self._to_record(item)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from lean_explore.api.client import ApiClient
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(
                "lean_explore api backend is unavailable; install lean_explore package"
            ) from exc

        api_key = os.getenv(self.backend_config.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(
                f"missing API key environment variable: {self.backend_config.api_key_env}"
            )

        client = ApiClient(api_key=api_key, timeout=float(self.backend_config.api_timeout_seconds))
        client.base_url = self.backend_config.api_base_url.rstrip("/")
        self._client = client
        return self._client

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


__all__ = ["LeanExploreApiBackend"]
