from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import psutil
import pytest

from lean_mcp_toolkit.app import ToolkitServer
from lean_mcp_toolkit.backends import BackendKey
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_assist import (
    LspRunSnippetRequest,
    LspTheoremSoundnessRequest,
)
from lean_mcp_toolkit.groups.lsp_assist.service_impl import LspAssistServiceImpl
from lean_mcp_toolkit.groups.lsp_core.service_impl import LspCoreServiceImpl


def _has_real_lsp_runtime() -> bool:
    if shutil.which("lake") is None or shutil.which("lean") is None:
        return False
    try:
        __import__("leanclient")
    except Exception:
        return False
    return True


def _init_lake_project(base_dir: Path, project_name: str) -> tuple[Path, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["lake", "init", project_name],
        cwd=base_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    project_root = base_dir
    package_dir = project_root / project_name
    return project_root, package_dir


def _extract_client_process_handle(owner: object):
    seen_ids: set[int] = set()
    queue: list[object] = [owner]
    while queue:
        current = queue.pop(0)
        if id(current) in seen_ids:
            continue
        seen_ids.add(id(current))
        if isinstance(current, subprocess.Popen):
            return current
        for attr_name in (
            "process",
            "proc",
            "_proc",
            "_process",
            "server_process",
            "transport",
            "_transport",
            "server",
            "_server",
            "client",
            "_client",
        ):
            nested = getattr(current, attr_name, None)
            if nested is not None:
                queue.append(nested)
    return None


def _capture_process_tree(root_pid: int) -> set[int]:
    root = psutil.Process(root_pid)
    pids = {root.pid}
    for child in root.children(recursive=True):
        pids.add(child.pid)
    return pids


def _wait_for_pids_to_exit(pids: set[int], *, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if all(not psutil.pid_exists(pid) for pid in pids):
            return
        time.sleep(0.1)
    still_alive = sorted(pid for pid in pids if psutil.pid_exists(pid))
    raise AssertionError(f"processes still alive after cleanup: {still_alive}")


@pytest.mark.skipif(
    not _has_real_lsp_runtime(),
    reason="real LSP cleanup test requires leanclient and lean/lake toolchain",
)
def test_run_snippet_timeout_recycles_real_lsp_process_tree(tmp_path: Path) -> None:
    project_root, package_dir = _init_lake_project(tmp_path / "snippet_timeout", "CleanupCase")
    package_dir.mkdir(parents=True, exist_ok=True)
    source = package_dir / "Basic.lean"
    source.write_text("def x : Nat := 1\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(project_root)},
            "groups": {"enabled_groups": ["lsp_core"]},
            "lsp_core": {
                "run_snippet_default_timeout_seconds": 1,
                "run_snippet_max_timeout_seconds": 1,
            },
        }
    )
    service = LspCoreServiceImpl(config=cfg)
    manager = service.lsp_client_manager
    client = manager.get_client(project_root)
    client.open_file("CleanupCase/Basic.lean")
    client.get_diagnostics("CleanupCase/Basic.lean", inactivity_timeout=5.0)

    handle = _extract_client_process_handle(client)
    if handle is None:
        pytest.skip("unable to discover LeanLSPClient process handle")
    tracked_pids = _capture_process_tree(handle.pid)

    response = service.run_snippet(
        LspRunSnippetRequest.from_dict(
            {
                "project_root": str(project_root),
                "code": "partial def loop : IO Unit := loop\n#eval loop\n",
                "timeout_seconds": 1,
            }
        )
    )

    assert response.success is False
    _wait_for_pids_to_exit(tracked_pids)
    assert list(project_root.glob("_mcp_snippet_*.lean")) == []


@pytest.mark.skipif(
    not _has_real_lsp_runtime(),
    reason="real LSP cleanup test requires leanclient and lean/lake toolchain",
)
def test_theorem_soundness_timeout_recycles_real_lsp_process_tree(tmp_path: Path) -> None:
    project_root, package_dir = _init_lake_project(tmp_path / "theorem_soundness_timeout", "CleanupCase")
    package_dir.mkdir(parents=True, exist_ok=True)
    basic_source = package_dir / "Basic.lean"
    basic_source.write_text("theorem t : True := by\n  trivial\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(project_root)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "backends": {"lsp": {"diagnostics_timeout_seconds": 1}},
            "lsp_assist": {"enabled": True},
        }
    )
    service = LspAssistServiceImpl(config=cfg)
    manager = service.lsp_client_manager
    client = manager.get_client(project_root)
    client.open_file("CleanupCase/Basic.lean")
    client.get_diagnostics("CleanupCase/Basic.lean", inactivity_timeout=5.0)

    handle = _extract_client_process_handle(client)
    if handle is None:
        pytest.skip("unable to discover LeanLSPClient process handle")
    tracked_pids = _capture_process_tree(handle.pid)

    def _raise_timeout(*, client, rel_path, timeout_seconds):
        _ = client, rel_path, timeout_seconds
        raise TimeoutError("timed out")

    service._get_diagnostics_with_hard_timeout = _raise_timeout  # type: ignore[method-assign]

    response = service.run_theorem_soundness(
        LspTheoremSoundnessRequest.from_dict(
            {
                "project_root": str(project_root),
                "file_path": "CleanupCase/Basic.lean",
                "theorem_name": "CleanupCase.Basic.t",
                "scan_source": False,
            }
        )
    )

    assert response.success is False
    assert "timed out" in (response.error_message or "").lower()
    _wait_for_pids_to_exit(tracked_pids)
    assert list(project_root.glob("_mcp_verify_*.lean")) == []


@pytest.mark.skipif(
    not _has_real_lsp_runtime(),
    reason="real LSP cleanup test requires leanclient and lean/lake toolchain",
)
def test_toolkit_server_close_reaps_real_lsp_process_tree(tmp_path: Path) -> None:
    project_root, package_dir = _init_lake_project(tmp_path / "server_close", "CleanupCase")
    package_dir.mkdir(parents=True, exist_ok=True)
    source = package_dir / "Basic.lean"
    source.write_text("def x : Nat := 1\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(project_root)},
            "groups": {"enabled_groups": ["lsp_core"]},
        }
    )
    server = ToolkitServer.from_config(cfg)
    manager = server._backend_context.require(BackendKey.LSP_CLIENT_MANAGER)
    client = manager.get_client(project_root)
    client.open_file("CleanupCase/Basic.lean")
    client.get_diagnostics("CleanupCase/Basic.lean", inactivity_timeout=5.0)

    handle = _extract_client_process_handle(client)
    if handle is None:
        pytest.skip("unable to discover LeanLSPClient process handle")
    tracked_pids = _capture_process_tree(handle.pid)

    server.close()

    _wait_for_pids_to_exit(tracked_pids)
