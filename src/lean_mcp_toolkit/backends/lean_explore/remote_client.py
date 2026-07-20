"""HTTP client for a remote LeanExplore service."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import ssl
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from ...config import LeanExploreBackendConfig
from .base import LeanExploreRecord, LeanExploreSearchResult


@dataclass(slots=True, frozen=True)
class LeanExploreRemoteMetadata:
    status: str
    index_id: str | None
    lean_version: str | None
    mathlib_revision: str | None


@dataclass(slots=True)
class LeanExploreRemoteClient:
    """Small dependency-free client for the versioned LeanExplore HTTP API."""

    backend_config: LeanExploreBackendConfig
    api_key: str
    _opener: Any = field(default=None, init=False, repr=False)

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        params: dict[str, str | int] = {
            "q": query,
            "limit": int(limit),
        }
        if rerank_top is not None:
            params["rerank_top"] = int(rerank_top)
        if packages:
            params["packages"] = ",".join(packages)
        try:
            payload = self._request_json("GET", f"/search?{urllib.parse.urlencode(params)}")
        except _RemoteNotFound as exc:
            raise RuntimeError("remote LeanExplore search endpoint was not found") from exc
        raw_items = payload.get("results")
        if raw_items is None:
            raw_items = []
        if not isinstance(raw_items, list):
            raise RuntimeError("remote LeanExplore search response `results` must be a list")
        items = tuple(self._to_record(item) for item in raw_items)
        processing_time = payload.get("processing_time_ms")
        return LeanExploreSearchResult(
            query=str(payload.get("query") or query),
            processing_time_ms=(int(processing_time) if processing_time is not None else None),
            items=items,
        )

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        try:
            payload = self._request_json("GET", f"/declarations/{int(declaration_id)}")
        except _RemoteNotFound:
            return None
        return self._to_record(payload)

    def health(self) -> LeanExploreRemoteMetadata:
        try:
            payload = self._request_json("GET", self.backend_config.api_health_path)
        except _RemoteNotFound as exc:
            raise RuntimeError("remote LeanExplore health endpoint was not found") from exc
        return LeanExploreRemoteMetadata(
            status=str(payload.get("status") or ""),
            index_id=self._optional_str(payload.get("index_id")),
            lean_version=self._optional_str(payload.get("lean_version")),
            mathlib_revision=self._optional_str(payload.get("mathlib_revision")),
        )

    def close(self) -> None:
        self._opener = None

    def _request_json(self, method: str, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url=self._build_url(path),
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        total_attempts = max(1, 1 + int(self.backend_config.api_retry_count))
        for attempt in range(total_attempts):
            try:
                with self._get_opener().open(
                    request,
                    timeout=float(self.backend_config.api_timeout_seconds),
                ) as response:
                    body = response.read().decode("utf-8")
                    return self._decode_object(body)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 404:
                    raise _RemoteNotFound() from exc
                if exc.code in {429, 500, 502, 503, 504} and attempt + 1 < total_attempts:
                    self._sleep_before_retry()
                    continue
                raise RuntimeError(
                    f"remote LeanExplore request failed with HTTP {exc.code}: {body}"
                ) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt + 1 < total_attempts:
                    self._sleep_before_retry()
                    continue
                raise RuntimeError(f"remote LeanExplore request failed: {exc}") from exc
        raise RuntimeError("remote LeanExplore request failed")  # pragma: no cover

    def _get_opener(self) -> Any:
        if self._opener is not None:
            return self._opener
        handlers: list[Any] = []
        if not self.backend_config.api_trust_env:
            handlers.append(urllib.request.ProxyHandler({}))
        context = None
        if not self.backend_config.api_verify_ssl:
            context = ssl._create_unverified_context()  # noqa: SLF001
        if context is not None:
            handlers.append(urllib.request.HTTPSHandler(context=context))
        self._opener = urllib.request.build_opener(*handlers)
        return self._opener

    def _build_url(self, path: str) -> str:
        base = self.backend_config.api_base_url.rstrip("/")
        suffix = path.strip()
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        return base + suffix

    def _sleep_before_retry(self) -> None:
        delay = max(0.0, float(self.backend_config.api_retry_backoff_seconds))
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _decode_object(body: str) -> dict[str, Any]:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("remote LeanExplore response is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("remote LeanExplore response must be a JSON object")
        return payload

    @staticmethod
    def _to_record(payload: Any) -> LeanExploreRecord:
        if not isinstance(payload, dict):
            raise RuntimeError("remote LeanExplore declaration must be a JSON object")
        return LeanExploreRecord(
            id=int(payload.get("id", 0)),
            name=str(payload.get("name") or ""),
            module=LeanExploreRemoteClient._optional_str(payload.get("module")),
            docstring=LeanExploreRemoteClient._optional_str(payload.get("docstring")),
            source_text=LeanExploreRemoteClient._optional_str(payload.get("source_text")),
            source_link=LeanExploreRemoteClient._optional_str(payload.get("source_link")),
            dependencies=LeanExploreRemoteClient._optional_str(payload.get("dependencies")),
            informalization=LeanExploreRemoteClient._optional_str(payload.get("informalization")),
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        return str(value) if value is not None else None


class _RemoteNotFound(Exception):
    pass


__all__ = ["LeanExploreRemoteClient", "LeanExploreRemoteMetadata"]
