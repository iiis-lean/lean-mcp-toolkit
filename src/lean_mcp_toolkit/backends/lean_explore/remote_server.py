"""Standalone HTTP service for a local LeanExplore index and model runtime."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hmac
import os
import re
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from ...config import LeanExploreBackendConfig, SearchCoreConfig
from .base import LeanExploreBackend, LeanExploreRecord, LeanExploreSearchResult
from .local_backend import LeanExploreLocalBackend
from .version_map import resolve_toolchain_id


@dataclass(slots=True, frozen=True)
class LeanExploreRemoteServerConfig:
    lean_version: str = "4.28.0"
    host: str = "127.0.0.1"
    port: int = 18081
    api_key_env: str = "LEANEXPLORE_API_KEY"
    require_api_key: bool = True
    warmup: bool = True
    warmup_query: str = "Nat.succ"
    warmup_rerank_top: int = 50
    default_rerank_top: int = 50
    cache_dir: str | None = None
    data_dir: str | None = None
    packages_root: str | None = None
    local_timeout_seconds: int = 120
    log_level: str = "info"


def create_remote_server_app(
    server_config: LeanExploreRemoteServerConfig,
    *,
    backend: LeanExploreBackend | None = None,
) -> FastAPI:
    """Create one single-process remote service around a local LeanExplore backend."""

    index_id = resolve_toolchain_id(server_config.lean_version)
    active_backend = backend or LeanExploreLocalBackend(
        backend_config=LeanExploreBackendConfig(
            mode="local",
            cache_dir=server_config.cache_dir,
            data_dir=server_config.data_dir,
            packages_root=server_config.packages_root,
            local_timeout_seconds=server_config.local_timeout_seconds,
        ),
        search_config=SearchCoreConfig(
            mathlib_lean_version=server_config.lean_version,
            require_mathlib=True,
        ),
    )
    state: dict[str, str | None] = {
        "status": "starting",
        "mathlib_revision": None,
    }
    operation_lock = asyncio.Lock()

    def _configured_api_key() -> str:
        return os.getenv(server_config.api_key_env, "").strip()

    def _authorize(authorization: str | None = Header(default=None)) -> None:
        if not server_config.require_api_key:
            return
        api_key = _configured_api_key()
        if not api_key:
            raise HTTPException(status_code=503, detail="LeanExplore API key is not configured")
        expected = f"Bearer {api_key}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if server_config.require_api_key and not _configured_api_key():
            raise RuntimeError(
                f"missing API key environment variable: {server_config.api_key_env}"
            )
        try:
            if server_config.warmup:
                warmup_result = await asyncio.to_thread(
                    active_backend.search,
                    query=server_config.warmup_query,
                    limit=1,
                    rerank_top=server_config.warmup_rerank_top,
                    packages=("Mathlib",),
                )
                if not warmup_result.items:
                    raise RuntimeError("LeanExplore warmup returned no Mathlib declarations")
                state["mathlib_revision"] = _find_mathlib_revision(warmup_result)
            state["status"] = "ready"
            yield
        finally:
            state["status"] = "stopping"
            close = getattr(active_backend, "close", None)
            if callable(close):
                await asyncio.to_thread(close)

    app = FastAPI(
        title="Lean MCP Toolkit LeanExplore Service",
        version="1.0.0",
        lifespan=_lifespan,
    )

    def _health_payload() -> dict[str, str | None]:
        return {
            "status": state["status"],
            "index_id": index_id,
            "lean_version": server_config.lean_version,
            "mathlib_revision": state["mathlib_revision"],
        }

    @app.get("/health")
    @app.get("/api/v2/health")
    def health() -> dict[str, str | None]:
        return _health_payload()

    @app.get("/api/v2/search", dependencies=[Depends(_authorize)])
    async def search(
        q: str = Query(..., min_length=1),
        limit: int = Query(20, ge=1, le=100),
        rerank_top: int | None = Query(None, ge=0, le=200),
        packages: str | None = Query(None),
    ) -> dict[str, Any]:
        package_values = _parse_packages(packages)
        effective_rerank_top = (
            server_config.default_rerank_top if rerank_top is None else rerank_top
        )
        try:
            async with operation_lock:
                result = await asyncio.to_thread(
                    active_backend.search,
                    query=q,
                    limit=limit,
                    rerank_top=effective_rerank_top,
                    packages=package_values,
                )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"LeanExplore search failed: {exc}") from exc
        return {
            "query": result.query,
            "count": len(result.items),
            "processing_time_ms": result.processing_time_ms,
            "results": [_record_payload(item) for item in result.items],
        }

    @app.get("/api/v2/declarations/{declaration_id}", dependencies=[Depends(_authorize)])
    async def get_declaration(declaration_id: int) -> dict[str, Any]:
        try:
            async with operation_lock:
                item = await asyncio.to_thread(active_backend.get_by_id, declaration_id)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"LeanExplore declaration lookup failed: {exc}",
            ) from exc
        if item is None:
            raise HTTPException(status_code=404, detail="declaration not found")
        return _record_payload(item)

    return app


def _parse_packages(packages: str | None) -> tuple[str, ...] | None:
    if packages is None:
        return None
    values = tuple(item.strip() for item in packages.split(",") if item.strip())
    return values or None


def _record_payload(record: LeanExploreRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "module": record.module,
        "docstring": record.docstring,
        "source_text": record.source_text,
        "source_link": record.source_link,
        "dependencies": record.dependencies,
        "informalization": record.informalization,
    }


def _find_mathlib_revision(result: LeanExploreSearchResult) -> str | None:
    for item in result.items:
        source_link = item.source_link or ""
        match = re.search(r"github\.com/leanprover-community/mathlib4/blob/([0-9a-f]{40})", source_link)
        if match:
            return match.group(1)
    return None


def _parse_args(argv: list[str] | None = None) -> LeanExploreRemoteServerConfig:
    parser = argparse.ArgumentParser(description="Serve a local LeanExplore index over HTTP.")
    parser.add_argument("--lean-version", default="4.28.0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--api-key-env", default="LEANEXPLORE_API_KEY")
    parser.add_argument("--allow-unauthenticated", action="store_true")
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--warmup-query", default="Nat.succ")
    parser.add_argument("--warmup-rerank-top", type=int, default=50)
    parser.add_argument("--default-rerank-top", type=int, default=50)
    parser.add_argument("--cache-dir")
    parser.add_argument("--data-dir")
    parser.add_argument("--packages-root")
    parser.add_argument("--local-timeout-seconds", type=int, default=120)
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args(argv)
    return LeanExploreRemoteServerConfig(
        lean_version=args.lean_version,
        host=args.host,
        port=args.port,
        api_key_env=args.api_key_env,
        require_api_key=not args.allow_unauthenticated,
        warmup=not args.no_warmup,
        warmup_query=args.warmup_query,
        warmup_rerank_top=args.warmup_rerank_top,
        default_rerank_top=args.default_rerank_top,
        cache_dir=args.cache_dir,
        data_dir=args.data_dir,
        packages_root=args.packages_root,
        local_timeout_seconds=args.local_timeout_seconds,
        log_level=args.log_level,
    )


def main(argv: list[str] | None = None) -> None:
    server_config = _parse_args(argv)
    import uvicorn

    app = create_remote_server_app(server_config)
    uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        workers=1,
    )


if __name__ == "__main__":
    main()


__all__ = [
    "LeanExploreRemoteServerConfig",
    "create_remote_server_app",
    "main",
]
