"""Remote HTTP LeanExplore backend adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ...config import LeanExploreBackendConfig, SearchCoreConfig
from .base import LeanExploreRecord, LeanExploreSearchResult
from .remote_client import LeanExploreRemoteClient, LeanExploreRemoteMetadata


@dataclass(slots=True)
class LeanExploreApiBackend:
    """Adapter around a remote LeanExplore HTTP service."""

    backend_config: LeanExploreBackendConfig
    search_config: SearchCoreConfig = field(default_factory=SearchCoreConfig)
    _client: LeanExploreRemoteClient | None = field(default=None, init=False, repr=False)
    _metadata: LeanExploreRemoteMetadata | None = field(default=None, init=False, repr=False)

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        return self._get_client().search(
            query=query,
            limit=limit,
            rerank_top=rerank_top,
            packages=packages,
        )

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        return self._get_client().get_by_id(declaration_id)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._metadata = None

    def recycle(self) -> None:
        self.close()

    def validate_startup(self) -> None:
        """Fail before serving when required API configuration is unusable."""

        self._configured_api_key()
        if self.backend_config.api_verify_on_startup:
            self._get_client()

    def _get_client(self) -> LeanExploreRemoteClient:
        if self._client is not None:
            return self._client

        api_key = self._configured_api_key()
        client = LeanExploreRemoteClient(
            backend_config=self.backend_config,
            api_key=api_key,
        )
        if self.backend_config.api_verify_on_startup:
            try:
                metadata = client.health()
                self._validate_metadata(metadata)
            except Exception:
                client.close()
                raise
            self._metadata = metadata
        self._client = client
        return client

    def _configured_api_key(self) -> str:
        api_key = os.getenv(self.backend_config.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(
                f"missing API key environment variable: {self.backend_config.api_key_env}"
            )
        return api_key

    def _validate_metadata(self, metadata: LeanExploreRemoteMetadata) -> None:
        if metadata.status.strip().lower() not in {"ok", "ready"}:
            raise RuntimeError(
                f"remote LeanExplore service is not ready: status={metadata.status!r}"
            )
        expected = self.search_config.mathlib_lean_version.strip()
        actual = (metadata.lean_version or "").strip()
        if not actual:
            raise RuntimeError("remote LeanExplore health response is missing `lean_version`")
        if actual != expected:
            raise RuntimeError(
                "remote LeanExplore Lean version mismatch: "
                f"expected {expected}, got {actual}"
            )


__all__ = ["LeanExploreApiBackend"]
