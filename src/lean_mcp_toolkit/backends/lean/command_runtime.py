"""Lean/Lake command runtime used by diagnostics service."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import threading
from typing import Iterator

from ...config import LeanCommandBackendConfig, ToolchainConfig
from .command_models import CommandResult


@dataclass(slots=True)
class LeanCommandRuntime:
    """Execute Lean/Lake commands with project/env normalization.

    Concurrency configuration is wired here. Actual parallel execution remains
    driven by the caller; runtime limits are enforced when enabled.
    """

    backend_config: LeanCommandBackendConfig
    toolchain_config: ToolchainConfig
    _lean_sem: threading.BoundedSemaphore = field(init=False, repr=False)
    _lake_sem: threading.BoundedSemaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lean_sem = threading.BoundedSemaphore(
            max(1, self.backend_config.max_concurrent_lean_checks)
        )
        self._lake_sem = threading.BoundedSemaphore(
            max(1, self.backend_config.max_concurrent_lake_build)
        )

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None,
    ) -> CommandResult:
        cmd = self._lake_prefix() + ["build"]
        if jobs is not None and jobs > 0:
            cmd.extend(["-j", str(jobs)])
        if target_facet:
            cmd.extend(f"{target}:{target_facet}" for target in module_targets)
        else:
            cmd.extend(module_targets)
        with self._lake_guard():
            return self._run_command(
                args=tuple(cmd),
                cwd=project_root,
                timeout_s=timeout_s,
            )

    def run_lean_json(
        self,
        *,
        project_root: Path,
        rel_file: str,
        timeout_s: int | None,
    ) -> CommandResult:
        if self.toolchain_config.use_lake_env_for_lean:
            cmd = self._lake_prefix() + [
                "env",
                self.toolchain_config.lean_bin,
                "--json",
                rel_file,
            ]
        else:
            cmd = self._lean_prefix() + ["--json", rel_file]

        with self._lean_guard():
            return self._run_command(
                args=tuple(cmd),
                cwd=project_root,
                timeout_s=timeout_s,
            )

    def run_lean_json_batch(
        self,
        *,
        project_root: Path,
        rel_files: tuple[str, ...],
        timeout_s: int | None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        if not rel_files:
            return tuple()

        max_workers = max(
            1,
            min(len(rel_files), self.backend_config.max_concurrent_lean_checks),
        )
        if max_workers <= 1:
            return tuple(
                (
                    rel_file,
                    self.run_lean_json(
                        project_root=project_root,
                        rel_file=rel_file,
                        timeout_s=timeout_s,
                    ),
                )
                for rel_file in rel_files
            )

        indexed_results: list[tuple[str, CommandResult] | None] = [None] * len(rel_files)
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="lean-json",
        ) as executor:
            future_to_index: dict[object, int] = {}
            for idx, rel_file in enumerate(rel_files):
                future = executor.submit(
                    self.run_lean_json,
                    project_root=project_root,
                    rel_file=rel_file,
                    timeout_s=timeout_s,
                )
                future_to_index[future] = idx

            for future in as_completed(tuple(future_to_index.keys())):
                idx = future_to_index[future]
                rel_file = rel_files[idx]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - safety fallback
                    result = self._unexpected_lean_json_error(rel_file=rel_file, exc=exc)
                indexed_results[idx] = (rel_file, result)

        finalized: list[tuple[str, CommandResult]] = []
        for idx, rel_file in enumerate(rel_files):
            item = indexed_results[idx]
            if item is None:  # pragma: no cover - defensive fallback
                item = (
                    rel_file,
                    self._unexpected_lean_json_error(
                        rel_file=rel_file,
                        exc=RuntimeError("missing batch result"),
                    ),
                )
            finalized.append(item)
        return tuple(finalized)

    def _lake_prefix(self) -> list[str]:
        if self.toolchain_config.prefer_elan:
            return [self.toolchain_config.elan_bin, "run", self.toolchain_config.lake_bin]
        return [self.toolchain_config.lake_bin]

    def _lean_prefix(self) -> list[str]:
        if self.toolchain_config.prefer_elan:
            return [self.toolchain_config.elan_bin, "run", self.toolchain_config.lean_bin]
        return [self.toolchain_config.lean_bin]

    def _runtime_env(self) -> dict[str, str]:
        env = dict()
        for key, value in self.toolchain_config.extra_env.items():
            env[str(key)] = str(value)
        return env

    @contextmanager
    def _lean_guard(self) -> Iterator[None]:
        with self._maybe_semaphore(self._lean_sem):
            yield

    @contextmanager
    def _lake_guard(self) -> Iterator[None]:
        with self._maybe_semaphore(self._lake_sem):
            yield

    def _maybe_semaphore(self, sem: threading.BoundedSemaphore):
        if not self.backend_config.enable_concurrency_limits:
            return nullcontext()

        @contextmanager
        def _guard() -> Iterator[None]:
            sem.acquire()
            try:
                yield
            finally:
                sem.release()

        return _guard()

    def _run_command(
        self,
        *,
        args: tuple[str, ...],
        cwd: Path,
        timeout_s: int | None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                list(args),
                cwd=str(cwd),
                env=self._merge_env(),
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            return CommandResult(
                args=args,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                args=args,
                returncode=124,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                timed_out=True,
            )
        except FileNotFoundError as exc:
            return CommandResult(
                args=args,
                returncode=127,
                stdout="",
                stderr=str(exc),
                timed_out=False,
            )

    def _merge_env(self) -> dict[str, str] | None:
        extra = self._runtime_env()
        if not extra:
            return None
        import os

        merged = dict(os.environ)
        merged.update(extra)
        return merged

    def _unexpected_lean_json_error(self, *, rel_file: str, exc: Exception) -> CommandResult:
        if self.toolchain_config.use_lake_env_for_lean:
            args = tuple(
                self._lake_prefix()
                + [
                    "env",
                    self.toolchain_config.lean_bin,
                    "--json",
                    rel_file,
                ]
            )
        else:
            args = tuple(self._lean_prefix() + ["--json", rel_file])
        return CommandResult(
            args=args,
            returncode=70,
            stdout="",
            stderr=f"unexpected batch worker failure: {exc}",
            timed_out=False,
        )
