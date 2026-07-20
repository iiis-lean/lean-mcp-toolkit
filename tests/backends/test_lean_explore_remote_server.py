from __future__ import annotations

from dataclasses import dataclass, field

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from lean_mcp_toolkit.backends.lean_explore import LeanExploreRecord, LeanExploreSearchResult
from lean_mcp_toolkit.backends.lean_explore.remote_server import (
    LeanExploreRemoteServerConfig,
    create_remote_server_app,
)


@dataclass(slots=True)
class _FakeBackend:
    searches: list[dict[str, object]] = field(default_factory=list)
    get_ids: list[int] = field(default_factory=list)
    close_calls: int = 0

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        self.searches.append(
            {
                "query": query,
                "limit": limit,
                "rerank_top": rerank_top,
                "packages": packages,
            }
        )
        return LeanExploreSearchResult(
            query=query,
            processing_time_ms=6,
            items=(_record(),),
        )

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        self.get_ids.append(declaration_id)
        return _record() if declaration_id == 7 else None

    def close(self) -> None:
        self.close_calls += 1


def _record() -> LeanExploreRecord:
    return LeanExploreRecord(
        id=7,
        name="Nat.succ",
        module="Mathlib.Data.Nat.Basic",
        docstring=None,
        source_text="def Nat.succ",
        source_link=(
            "https://github.com/leanprover-community/mathlib4/blob/"
            "aae61ae084c21995ee248964a81e3750ad0db2db/Mathlib/Data/Nat/Basic.lean"
        ),
        dependencies=None,
        informalization="successor",
    )


def test_remote_server_search_get_auth_health_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    backend = _FakeBackend()
    app = create_remote_server_app(
        LeanExploreRemoteServerConfig(
            lean_version="4.32.0",
            api_key_env="LEANEXPLORE_TEST_KEY",
            warmup=True,
            warmup_query="warmup",
            warmup_rerank_top=25,
        ),
        backend=backend,
    )

    with TestClient(app) as client:
        health = client.get("/api/v2/health")
        unauthorized = client.get("/api/v2/search", params={"q": "successor"})
        search = client.get(
            "/api/v2/search",
            params={
                "q": "successor",
                "limit": 3,
                "rerank_top": 50,
                "packages": "Mathlib,Std",
            },
            headers={"Authorization": "Bearer test-secret"},
        )
        get_item = client.get(
            "/api/v2/declarations/7",
            headers={"Authorization": "Bearer test-secret"},
        )
        missing = client.get(
            "/api/v2/declarations/999",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert health.status_code == 200
    assert health.json() == {
        "status": "ready",
        "index_id": "20260714_172516",
        "lean_version": "4.32.0",
        "mathlib_revision": "aae61ae084c21995ee248964a81e3750ad0db2db",
    }
    assert unauthorized.status_code == 401
    assert search.status_code == 200
    assert search.json()["results"][0]["name"] == "Nat.succ"
    assert get_item.status_code == 200
    assert missing.status_code == 404
    assert backend.searches == [
        {
            "query": "warmup",
            "limit": 1,
            "rerank_top": 25,
            "packages": ("Mathlib",),
        },
        {
            "query": "successor",
            "limit": 3,
            "rerank_top": 50,
            "packages": ("Mathlib", "Std"),
        },
    ]
    assert backend.get_ids == [7, 999]
    assert backend.close_calls == 1


def test_remote_server_keeps_legacy_428_default() -> None:
    backend = _FakeBackend()
    app = create_remote_server_app(
        LeanExploreRemoteServerConfig(
            require_api_key=False,
            warmup=False,
        ),
        backend=backend,
    )

    with TestClient(app) as client:
        health = client.get("/health")

    assert health.json()["lean_version"] == "4.28.0"
    assert health.json()["index_id"] == "20260217_050001"
