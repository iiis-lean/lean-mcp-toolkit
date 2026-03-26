"""LeanInteract backend for declarations extraction."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from ...config import LeanInteractBackendConfig, ToolchainConfig
from ..lean.path import LeanPath
from .base import DeclarationsBackendRequest, DeclarationsBackendResponse

_LEAN_VERSION_TO_REPL_REV: dict[str, str] = {
    "v4.20.0": "v1.3.9",
    "v4.20.1": "v1.3.9",
    "v4.21.0": "v1.3.9",
    "v4.22.0": "v1.3.9",
    "v4.23.0": "v1.3.9",
    "v4.24.0": "v1.3.9",
    "v4.25.0": "v1.3.9",
    "v4.25.1": "v1.3.9",
    "v4.26.0": "v1.3.9",
    "v4.27.0": "v1.3.14",
    "v4.28.0": "v1.3.14",
}


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
                error_message=f"lean_interact execution failed: {self._format_exception(exc)}",
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
        auto_repl_rev = self.backend_config.repl_rev is None
        repl_rev = self._resolve_repl_rev(project_root=project_root)
        config_kwargs: dict[str, Any] = {
            "project": project,
            "build_repl": self.backend_config.build_repl,
            "force_pull_repl": self.backend_config.force_pull_repl or auto_repl_rev,
            "lake_path": self.toolchain_config.lake_bin,
            "memory_hard_limit_mb": self.backend_config.memory_hard_limit_mb,
            "enable_incremental_optimization": (
                self.backend_config.enable_incremental_optimization
            ),
            "enable_parallel_elaboration": (
                self.backend_config.enable_parallel_elaboration
            ),
            "verbose": self.backend_config.verbose,
        }
        if repl_rev is not None:
            config_kwargs["repl_rev"] = repl_rev
        if self.backend_config.repl_git is not None:
            config_kwargs["repl_git"] = self.backend_config.repl_git
        if self.backend_config.cache_dir is not None:
            config_kwargs["cache_dir"] = self.backend_config.cache_dir
        config = lean_interact["LeanREPLConfig"](**config_kwargs)
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

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        message = str(exc).strip()
        if message:
            return message
        return exc.__class__.__name__

    def _resolve_repl_rev(self, *, project_root: Path) -> str | None:
        if self.backend_config.repl_rev is not None:
            return self.backend_config.repl_rev
        lean_version = self._read_project_lean_version(project_root)
        if lean_version is None:
            return None
        return _LEAN_VERSION_TO_REPL_REV.get(self._normalize_lean_version(lean_version))

    @staticmethod
    def _read_project_lean_version(project_root: Path) -> str | None:
        toolchain_file = project_root / "lean-toolchain"
        try:
            raw = toolchain_file.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        if not raw:
            return None
        return LeanInteractDeclarationsBackend._normalize_lean_version(raw)

    @staticmethod
    def _normalize_lean_version(raw: str) -> str:
        text = raw.strip()
        if text.startswith("leanprover/lean4:"):
            text = text.removeprefix("leanprover/lean4:")
        if "-rc" in text:
            text = text.split("-rc", 1)[0]
        return text
