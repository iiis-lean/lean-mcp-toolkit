"""Shared LeanInteract runtime manager."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from ..config import LeanInteractBackendConfig, ToolchainConfig

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


class LeanInteractRuntimeManager:
    """Manage shared LeanInteract runtimes keyed by project root."""

    def __init__(
        self,
        *,
        toolchain_config: ToolchainConfig,
        backend_config: LeanInteractBackendConfig,
    ):
        self.toolchain_config = toolchain_config
        self.backend_config = backend_config
        self._runtime_lock = Lock()
        self._runtimes: dict[str, Any] = {}

    def close(self) -> None:
        with self._runtime_lock:
            runtimes = tuple(self._runtimes.values())
            self._runtimes.clear()
        for runtime in runtimes:
            try:
                close = getattr(runtime, "close", None)
                if callable(close):
                    close()
                    continue
                kill = getattr(runtime, "kill", None)
                if callable(kill):
                    kill()
            except Exception:
                continue

    def run(
        self,
        *,
        project_root: Path,
        request: Any,
        timeout: float | None,
    ) -> Any:
        runtime = self._get_runtime(project_root)
        return runtime.run(request, timeout=timeout)

    def run_batch(
        self,
        *,
        project_root: Path,
        requests: tuple[Any, ...],
        timeout_per_req: float | None,
    ) -> tuple[Any, ...]:
        if not requests:
            return tuple()
        runtime = self._get_runtime(project_root)
        if hasattr(runtime, "run_batch"):
            responses = runtime.run_batch(
                list(requests),
                timeout_per_cmd=timeout_per_req,
                show_progress=False,
            )
            return tuple(responses)
        return tuple(runtime.run(request, timeout=timeout_per_req) for request in requests)

    def make_file_command(self, *, rel_file: str, declarations: bool = True) -> Any:
        lean_interact = self._load_lean_interact()
        return lean_interact["FileCommand"](path=rel_file, declarations=declarations)

    def lean_error_cls(self) -> type[Any]:
        return self._load_lean_interact()["LeanError"]

    def _get_runtime(self, project_root: Path) -> Any:
        key = str(project_root)
        with self._runtime_lock:
            existing = self._runtimes.get(key)
            if existing is not None:
                return existing
            runtime = self._create_runtime(project_root)
            self._runtimes[key] = runtime
            return runtime

    def _create_runtime(self, project_root: Path) -> Any:
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
        if self.backend_config.use_server_pool:
            return lean_interact["LeanServerPool"](
                config,
                num_workers=self.backend_config.pool_workers,
            )
        server_cls = (
            lean_interact["AutoLeanServer"]
            if self.backend_config.use_auto_server
            else lean_interact["LeanServer"]
        )
        return server_cls(config)

    def _load_lean_interact(self) -> dict[str, Any]:
        try:
            from lean_interact import AutoLeanServer, FileCommand, LeanREPLConfig, LeanServer, LocalProject
            from lean_interact.interface import LeanError
            from lean_interact.pool import LeanServerPool
        except Exception as exc:  # pragma: no cover - dependency boundary
            raise RuntimeError(f"failed to import lean_interact: {exc}") from exc

        return {
            "LeanREPLConfig": LeanREPLConfig,
            "LeanServer": LeanServer,
            "AutoLeanServer": AutoLeanServer,
            "LeanServerPool": LeanServerPool,
            "LocalProject": LocalProject,
            "FileCommand": FileCommand,
            "LeanError": LeanError,
        }

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
        return LeanInteractRuntimeManager._normalize_lean_version(raw)

    @staticmethod
    def _normalize_lean_version(raw: str) -> str:
        text = raw.strip()
        if text.startswith("leanprover/lean4:"):
            text = text.removeprefix("leanprover/lean4:")
        if "-rc" in text:
            text = text.split("-rc", 1)[0]
        return text
