from pathlib import Path

from lean_mcp_toolkit.backends.lsp import LeanLSPClientManager
from lean_mcp_toolkit.config import ToolkitConfig


class _FakeClient:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def test_lsp_client_manager_recycle_recreates_client(tmp_path: Path, monkeypatch) -> None:
    manager = LeanLSPClientManager(backend_config=ToolkitConfig().backends.lsp)
    created: list[_FakeClient] = []

    def _fake_create_client(project_root: Path, *, initial_build: bool = False) -> _FakeClient:
        _ = project_root, initial_build
        client = _FakeClient()
        created.append(client)
        return client

    monkeypatch.setattr(manager, "_create_client", _fake_create_client)

    first = manager.get_client(tmp_path)
    again = manager.get_client(tmp_path)
    manager.recycle_client(tmp_path)
    second = manager.get_client(tmp_path)

    assert first is again
    assert first is not second
    assert created[0].close_calls == 1
    assert created[1].close_calls == 0


def test_lsp_client_manager_close_all_closes_cached_clients(tmp_path: Path, monkeypatch) -> None:
    manager = LeanLSPClientManager(backend_config=ToolkitConfig().backends.lsp)
    created: list[_FakeClient] = []

    def _fake_create_client(project_root: Path, *, initial_build: bool = False) -> _FakeClient:
        _ = project_root, initial_build
        client = _FakeClient()
        created.append(client)
        return client

    monkeypatch.setattr(manager, "_create_client", _fake_create_client)

    manager.get_client(tmp_path / "A")
    manager.get_client(tmp_path / "B")
    manager.close_all()

    assert [client.close_calls for client in created] == [1, 1]
