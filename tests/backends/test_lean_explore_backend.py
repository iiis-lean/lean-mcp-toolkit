from dataclasses import dataclass

from lean_mcp_toolkit.backends.lean_explore.backend import LeanExploreBackendAdapter
from lean_mcp_toolkit.config import LeanExploreBackendConfig, SearchCoreConfig


@dataclass(slots=True)
class _FakeBackend:
    recycle_calls: int = 0
    close_calls: int = 0

    def recycle(self) -> None:
        self.recycle_calls += 1

    def close(self) -> None:
        self.close_calls += 1


def test_lean_explore_backend_adapter_recycle_clears_cached_backend() -> None:
    adapter = LeanExploreBackendAdapter(
        backend_config=LeanExploreBackendConfig(),
        search_config=SearchCoreConfig(),
    )
    fake = _FakeBackend()
    adapter._backend = fake

    adapter.recycle()

    assert fake.recycle_calls == 1
    assert adapter._backend is None


def test_lean_explore_backend_adapter_close_clears_cached_backend() -> None:
    adapter = LeanExploreBackendAdapter(
        backend_config=LeanExploreBackendConfig(),
        search_config=SearchCoreConfig(),
    )
    fake = _FakeBackend()
    adapter._backend = fake

    adapter.close()

    assert fake.close_calls == 1
    assert adapter._backend is None
