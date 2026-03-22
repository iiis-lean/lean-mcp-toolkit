"""Lean LSP client manager with per-project client reuse."""

from __future__ import annotations

from pathlib import Path
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

    @staticmethod
    def _create_client(project_root: Path, *, initial_build: bool = False) -> Any:
        try:
            from leanclient import LeanLSPClient
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(f"failed to import leanclient: {exc}") from exc
        return LeanLSPClient(str(project_root), initial_build=initial_build)
