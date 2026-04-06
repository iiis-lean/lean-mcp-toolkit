from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from lean_mcp_toolkit.app import ToolkitServer
from lean_mcp_toolkit.backends import BackendContext, BackendKey
from lean_mcp_toolkit.config import ToolkitConfig


@dataclass(slots=True)
class _FakeLspManager:
    recycled_roots: list[Path]

    def recycle_client(self, project_root: Path) -> None:
        self.recycled_roots.append(project_root.resolve())


@dataclass(slots=True)
class _FakeLeanInteractRuntimeManager:
    recycled_roots: list[Path]

    def recycle_runtime(self, project_root: Path) -> None:
        self.recycled_roots.append(project_root.resolve())


@dataclass(slots=True)
class _FakeLeanInteractBackend:
    runtime_manager: _FakeLeanInteractRuntimeManager


def _build_server(tmp_path: Path) -> ToolkitServer:
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    return ToolkitServer(config=cfg, api_prefix="/api/v1")


def test_toolkit_server_can_recycle_cached_backends(tmp_path: Path) -> None:
    server = _build_server(tmp_path)
    lsp_manager = _FakeLspManager(recycled_roots=[])
    interact_manager = _FakeLeanInteractRuntimeManager(recycled_roots=[])
    ctx = BackendContext()
    ctx.set(BackendKey.LSP_CLIENT_MANAGER, lsp_manager)
    ctx.set(
        BackendKey.DECLARATIONS_BACKENDS,
        {"lean_interact": _FakeLeanInteractBackend(runtime_manager=interact_manager)},
    )
    server._backend_context = ctx

    lsp_payload = server.recycle_lsp_backend()
    interact_payload = server.recycle_lean_interact_backend()

    assert lsp_payload["ok"] is True
    assert lsp_payload["backend"] == "lsp"
    assert lsp_manager.recycled_roots == [tmp_path.resolve()]

    assert interact_payload["ok"] is True
    assert interact_payload["backend"] == "lean_interact"
    assert interact_manager.recycled_roots == [tmp_path.resolve()]


def test_toolkit_server_recycle_reports_missing_backends(tmp_path: Path) -> None:
    server = _build_server(tmp_path)
    server._backend_context = BackendContext()

    lsp_payload = server.recycle_lsp_backend()
    interact_payload = server.recycle_lean_interact_backend()

    assert lsp_payload["ok"] is False
    assert "not initialized" in lsp_payload["message"]
    assert interact_payload["ok"] is False
    assert "not initialized" in interact_payload["message"]


def test_toolkit_server_fastapi_debug_recycle_routes(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    server = _build_server(tmp_path)
    lsp_manager = _FakeLspManager(recycled_roots=[])
    interact_manager = _FakeLeanInteractRuntimeManager(recycled_roots=[])
    ctx = BackendContext()
    ctx.set(BackendKey.LSP_CLIENT_MANAGER, lsp_manager)
    ctx.set(
        BackendKey.DECLARATIONS_BACKENDS,
        {"lean_interact": _FakeLeanInteractBackend(runtime_manager=interact_manager)},
    )
    server._backend_context = ctx

    client = TestClient(server.create_fastapi_app())

    lsp_resp = client.post("/api/v1/debug/backends/recycle/lsp", json={})
    interact_resp = client.post("/api/v1/debug/backends/recycle/lean_interact", json={})

    assert lsp_resp.status_code == 200
    assert lsp_resp.json()["ok"] is True
    assert interact_resp.status_code == 200
    assert interact_resp.json()["ok"] is True
    assert lsp_manager.recycled_roots == [tmp_path.resolve()]
    assert interact_manager.recycled_roots == [tmp_path.resolve()]
