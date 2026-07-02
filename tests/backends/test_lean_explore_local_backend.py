from types import SimpleNamespace

import pytest

from lean_mcp_toolkit.backends.lean_explore.local_backend import LeanExploreLocalBackend
from lean_mcp_toolkit.config import LeanExploreBackendConfig, SearchCoreConfig


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class _FakeModel:
    def __init__(self) -> None:
        self.to_calls: list[str] = []
        self.cpu_calls = 0

    def to(self, device: str) -> None:
        self.to_calls.append(device)

    def cpu(self) -> None:
        self.cpu_calls += 1


class _FakeModelClient:
    def __init__(self) -> None:
        self.model = _FakeModel()
        self.tokenizer = object()


class _FakeSearchEngine:
    def __init__(self) -> None:
        self.engine = _FakeAsyncEngine()
        self._embedding_client = _FakeModelClient()
        self._reranker_client = _FakeModelClient()
        self._faiss_informal_index = object()
        self._faiss_informal_id_map = [1]
        self._bm25_name_spaced = object()
        self._bm25_name_raw = object()
        self._all_declaration_ids = [1]


def test_local_backend_close_releases_search_engine_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LeanExploreLocalBackend, "_release_torch_cuda", staticmethod(lambda: None))
    backend = LeanExploreLocalBackend(
        backend_config=LeanExploreBackendConfig(),
        search_config=SearchCoreConfig(),
    )
    engine = _FakeSearchEngine()
    service = SimpleNamespace(engine=engine)
    embedding_client = engine._embedding_client
    reranker_client = engine._reranker_client
    backend._engine = engine
    backend._service = service

    backend.close()

    assert backend._engine is None
    assert backend._service is None
    assert service.engine is None
    assert engine.engine.disposed
    assert embedding_client.model is None
    assert embedding_client.tokenizer is None
    assert reranker_client.model is None
    assert reranker_client.tokenizer is None
    assert engine._embedding_client is None
    assert engine._reranker_client is None
    assert engine._faiss_informal_index is None
    assert engine._bm25_name_spaced is None
