"""LeanInteract backend for declarations extraction."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from ...config import LeanInteractBackendConfig, ToolchainConfig
from ..lean.path import LeanPath
from .base import DeclarationsBackendRequest, DeclarationsBackendResponse


class LeanInteractDeclarationsBackend:
    """Declarations backend implemented on top of LeanInteract."""

    backend_name = "lean_interact"

    def __init__(
        self,
        *,
        toolchain_config: ToolchainConfig,
        backend_config: LeanInteractBackendConfig,
    ):
        self.toolchain_config = toolchain_config
        self.backend_config = backend_config
        self._server_lock = Lock()
        self._servers: dict[str, Any] = {}

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        rel_file = LeanPath.from_dot(req.target_dot).to_rel_file()

        try:
            server = self._get_server(req.project_root)
            file_command = self._make_file_command(rel_file=rel_file)
            timeout = float(req.timeout_seconds) if req.timeout_seconds is not None else None
            response = server.run(file_command, timeout=timeout)
        except Exception as exc:
            return DeclarationsBackendResponse(
                success=False,
                error_message=f"lean_interact execution failed: {exc}",
                declarations=tuple(),
                messages=tuple(),
                sorries=tuple(),
            )

        if self._is_lean_error(response):
            return DeclarationsBackendResponse(
                success=False,
                error_message=self._lean_error_message(response),
                declarations=tuple(),
                messages=tuple(),
                sorries=tuple(),
            )

        declarations = self._collect_sequence(getattr(response, "declarations", None))
        messages = self._collect_sequence(getattr(response, "messages", None))
        sorries = self._collect_sequence(getattr(response, "sorries", None))

        if self._response_has_errors(response):
            return DeclarationsBackendResponse(
                success=False,
                error_message=self._format_response_errors(response),
                declarations=declarations,
                messages=messages,
                sorries=sorries,
            )

        return DeclarationsBackendResponse(
            success=True,
            error_message=None,
            declarations=declarations,
            messages=messages,
            sorries=sorries,
        )

    def _get_server(self, project_root: Path) -> Any:
        key = str(project_root)
        with self._server_lock:
            existing = self._servers.get(key)
            if existing is not None:
                return existing
            server = self._create_server(project_root)
            self._servers[key] = server
            return server

    def _create_server(self, project_root: Path) -> Any:
        lean_interact = self._load_lean_interact()
        project = lean_interact["LocalProject"](
            directory=str(project_root),
            auto_build=self.backend_config.project_auto_build,
            lake_path=self.toolchain_config.lake_bin,
        )
        config = lean_interact["LeanREPLConfig"](
            project=project,
            build_repl=self.backend_config.build_repl,
            force_pull_repl=self.backend_config.force_pull_repl,
            lake_path=self.toolchain_config.lake_bin,
            memory_hard_limit_mb=self.backend_config.memory_hard_limit_mb,
            enable_incremental_optimization=(
                self.backend_config.enable_incremental_optimization
            ),
            enable_parallel_elaboration=(
                self.backend_config.enable_parallel_elaboration
            ),
            verbose=self.backend_config.verbose,
        )
        server_cls = (
            lean_interact["AutoLeanServer"]
            if self.backend_config.use_auto_server
            else lean_interact["LeanServer"]
        )
        return server_cls(config)

    def _make_file_command(self, *, rel_file: str) -> Any:
        lean_interact = self._load_lean_interact()
        return lean_interact["FileCommand"](path=rel_file, declarations=True)

    def _load_lean_interact(self) -> dict[str, Any]:
        try:
            from lean_interact import AutoLeanServer, FileCommand, LeanREPLConfig, LeanServer, LocalProject
            from lean_interact.interface import LeanError
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(f"failed to import lean_interact: {exc}") from exc

        return {
            "LeanREPLConfig": LeanREPLConfig,
            "LeanServer": LeanServer,
            "AutoLeanServer": AutoLeanServer,
            "LocalProject": LocalProject,
            "FileCommand": FileCommand,
            "LeanError": LeanError,
        }

    def _is_lean_error(self, response: Any) -> bool:
        lean_error_cls = self._load_lean_interact()["LeanError"]
        return isinstance(response, lean_error_cls)

    @staticmethod
    def _lean_error_message(response: Any) -> str:
        message = getattr(response, "message", None)
        return str(message or "unknown LeanInteract error")

    @staticmethod
    def _response_has_errors(response: Any) -> bool:
        has_errors = getattr(response, "has_errors", None)
        if callable(has_errors):
            return bool(has_errors())
        return False

    @staticmethod
    def _format_response_errors(response: Any) -> str:
        messages = getattr(response, "messages", None)
        if not isinstance(messages, list) or not messages:
            return "LeanInteract response contains errors"
        errors = []
        for msg in messages:
            severity = getattr(msg, "severity", None)
            if severity != "error":
                continue
            data = getattr(msg, "data", None)
            if data:
                errors.append(str(data))
        if not errors:
            return "LeanInteract response contains errors"
        return "; ".join(errors[:3])

    @staticmethod
    def _collect_sequence(value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, tuple):
            return value
        return tuple()

