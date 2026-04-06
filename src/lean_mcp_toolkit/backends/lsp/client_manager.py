"""Lean LSP client manager with per-project client reuse."""

from __future__ import annotations

from pathlib import Path
import subprocess
from threading import Lock
from typing import Any

from ...config import LspBackendConfig


class LeanLSPClientManager:
    """Manage LeanLSPClient instances keyed by project root."""

    def __init__(self, *, backend_config: LspBackendConfig):
        self.backend_config = backend_config
        self._clients: dict[str, Any] = {}
        self._lock = Lock()

    def get_client(self, project_root: Path) -> Any:
        key = str(project_root.resolve())
        with self._lock:
            existing = self._clients.get(key)
            if existing is not None:
                return existing
            client = self._create_client(
                project_root,
                initial_build=self.backend_config.initial_build,
            )
            self._clients[key] = client
            return client

    def close_client(self, project_root: Path) -> None:
        client = self._pop_client(project_root)
        if client is not None:
            self._close_client(client)

    def recycle_client(self, project_root: Path) -> None:
        self.close_client(project_root)

    def close_all(self) -> None:
        with self._lock:
            clients = tuple(self._clients.values())
            self._clients.clear()
        for client in clients:
            self._close_client(client)

    def close(self) -> None:
        self.close_all()

    def _pop_client(self, project_root: Path) -> Any | None:
        key = str(project_root.resolve())
        with self._lock:
            return self._clients.pop(key, None)

    @staticmethod
    def _create_client(project_root: Path, *, initial_build: bool = False) -> Any:
        try:
            from leanclient import LeanLSPClient
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(f"failed to import leanclient: {exc}") from exc
        return LeanLSPClient(str(project_root), initial_build=initial_build)

    @classmethod
    def _close_client(cls, client: Any) -> None:
        for method_name in ("close", "shutdown", "stop", "kill", "terminate"):
            method = getattr(client, method_name, None)
            if callable(method):
                try:
                    method()
                    return
                except Exception:
                    continue
        cls._close_nested_resource(client)

    @classmethod
    def _close_nested_resource(cls, owner: Any) -> None:
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
        ):
            nested = getattr(owner, attr_name, None)
            if nested is None or nested is owner:
                continue
            if cls._close_process_like(nested):
                return
            for method_name in ("close", "shutdown", "stop", "kill", "terminate"):
                method = getattr(nested, method_name, None)
                if callable(method):
                    try:
                        method()
                        return
                    except Exception:
                        continue

    @staticmethod
    def _close_process_like(obj: Any) -> bool:
        if not isinstance(obj, subprocess.Popen):
            return False
        try:
            if obj.poll() is None:
                obj.terminate()
                try:
                    obj.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    obj.kill()
                    obj.wait(timeout=1.0)
        except Exception:
            return False
        return True
