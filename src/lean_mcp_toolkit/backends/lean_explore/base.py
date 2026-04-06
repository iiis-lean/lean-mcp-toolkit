"""Base protocol and models for LeanExplore backend adapters.

These adapters wrap the external ``lean-explore`` project:
https://github.com/justincasher/lean-explore
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import subprocess
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class LeanExploreRecord:
    """Toolkit projection of one lean-explore declaration record."""

    id: int
    name: str
    module: str | None
    docstring: str | None
    source_text: str | None
    source_link: str | None
    dependencies: str | None
    informalization: str | None


@dataclass(slots=True, frozen=True)
class LeanExploreSearchResult:
    query: str
    processing_time_ms: int | None
    items: tuple[LeanExploreRecord, ...]


class LeanExploreBackend(Protocol):
    """Unified interface for lean-explore local and remote adapters."""

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        ...

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        ...

    def close(self) -> None:
        ...

    def recycle(self) -> None:
        ...


def run_async(coro: Any, *, timeout_seconds: float | None = None) -> Any:
    """Run async coroutine from sync context, including nested-loop environments."""

    async def _runner() -> Any:
        if timeout_seconds is None:
            return await coro
        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_runner())

    result: Future[Any] = Future()

    def _worker() -> None:
        try:
            value = asyncio.run(_runner())
            result.set_result(value)
        except Exception as exc:  # pragma: no cover - defensive branch
            result.set_exception(exc)

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="lean-explore-async") as ex:
        ex.submit(_worker)
        return result.result()


def close_resource_best_effort(owner: Any) -> None:
    """Best-effort cleanup for backend client/service objects."""

    for method_name in ("close", "aclose", "shutdown", "stop", "kill", "terminate"):
        method = getattr(owner, method_name, None)
        if callable(method):
            try:
                result = method()
                if asyncio.iscoroutine(result):
                    run_async(result, timeout_seconds=5.0)
                return
            except Exception:
                continue

    for attr_name in (
        "process",
        "proc",
        "_proc",
        "_process",
        "client",
        "_client",
        "engine",
        "_engine",
        "service",
        "_service",
    ):
        nested = getattr(owner, attr_name, None)
        if nested is None or nested is owner:
            continue
        if isinstance(nested, subprocess.Popen):
            try:
                if nested.poll() is None:
                    nested.terminate()
                    try:
                        nested.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        nested.kill()
                        nested.wait(timeout=1.0)
            except Exception:
                pass
            return
        for method_name in ("close", "aclose", "shutdown", "stop", "kill", "terminate"):
            method = getattr(nested, method_name, None)
            if callable(method):
                try:
                    result = method()
                    if asyncio.iscoroutine(result):
                        run_async(result, timeout_seconds=5.0)
                    return
                except Exception:
                    continue


__all__ = [
    "LeanExploreBackend",
    "LeanExploreRecord",
    "LeanExploreSearchResult",
    "close_resource_best_effort",
    "run_async",
]
