"""Base protocol and models for LeanExplore backend adapters.

These adapters wrap the external ``lean-explore`` project:
https://github.com/justincasher/lean-explore
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
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


def run_async(coro: Any) -> Any:
    """Run async coroutine from sync context, including nested-loop environments."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: Future[Any] = Future()

    def _worker() -> None:
        try:
            value = asyncio.run(coro)
            result.set_result(value)
        except Exception as exc:  # pragma: no cover - defensive branch
            result.set_exception(exc)

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="lean-explore-async") as ex:
        ex.submit(_worker)
        return result.result()


__all__ = [
    "LeanExploreBackend",
    "LeanExploreRecord",
    "LeanExploreSearchResult",
    "run_async",
]
