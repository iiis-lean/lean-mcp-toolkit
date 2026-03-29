from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

from lean_mcp_toolkit.backends.lean import CommandResult
from lean_mcp_toolkit.backends.lean.command_runtime import LeanCommandRuntime
from lean_mcp_toolkit.config import LeanCommandBackendConfig, ToolchainConfig


def _runtime() -> LeanCommandRuntime:
    return LeanCommandRuntime(
        backend_config=LeanCommandBackendConfig(),
        toolchain_config=ToolchainConfig(),
    )


class _RecordingRuntime(LeanCommandRuntime):
    def __init__(self, *, backend_config: LeanCommandBackendConfig, toolchain_config: ToolchainConfig):
        super().__init__(backend_config=backend_config, toolchain_config=toolchain_config)
        self.recorded_args: tuple[str, ...] | None = None

    def _run_command(
        self,
        *,
        args: tuple[str, ...],
        cwd: Path,
        timeout_s: int | None,
        deadline_monotonic: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> CommandResult:
        _ = cwd, timeout_s, deadline_monotonic, cancel_event
        self.recorded_args = args
        return CommandResult(args=args, returncode=0, stdout="", stderr="")


def test_run_command_timeout_terminates_long_running_process(tmp_path: Path) -> None:
    runtime = _runtime()
    start = time.monotonic()
    result = runtime._run_command(
        args=(sys.executable, "-c", "import time; time.sleep(5)"),
        cwd=tmp_path,
        timeout_s=1,
        deadline_monotonic=None,
        cancel_event=None,
    )
    elapsed = time.monotonic() - start

    assert result.timed_out is True
    assert result.returncode == 124
    assert elapsed < 3.0


def test_run_command_cancel_event_terminates_long_running_process(tmp_path: Path) -> None:
    runtime = _runtime()
    cancel_event = threading.Event()

    def _cancel_soon() -> None:
        time.sleep(0.2)
        cancel_event.set()

    worker = threading.Thread(target=_cancel_soon)
    worker.start()
    start = time.monotonic()
    result = runtime._run_command(
        args=(sys.executable, "-c", "import time; time.sleep(5)"),
        cwd=tmp_path,
        timeout_s=None,
        deadline_monotonic=None,
        cancel_event=cancel_event,
    )
    elapsed = time.monotonic() - start
    worker.join(timeout=1.0)

    assert result.timed_out is True
    assert result.returncode == 124
    assert "cancelled" in result.stderr
    assert elapsed < 3.0


def test_run_lake_build_does_not_include_jobs_flag(tmp_path: Path) -> None:
    runtime = _RecordingRuntime(
        backend_config=LeanCommandBackendConfig(),
        toolchain_config=ToolchainConfig(),
    )

    result = runtime.run_lake_build(
        project_root=tmp_path,
        module_targets=("Foo.Bar",),
        target_facet="deps",
        timeout_s=10,
    )

    assert result.ok is True
    assert runtime.recorded_args == ("lake", "build", "Foo.Bar:deps")


def test_run_lean_json_omits_threads_flag_by_default(tmp_path: Path) -> None:
    runtime = _RecordingRuntime(
        backend_config=LeanCommandBackendConfig(lean_json_threads=None),
        toolchain_config=ToolchainConfig(),
    )

    result = runtime.run_lean_json(
        project_root=tmp_path,
        rel_file="Foo/Bar.lean",
        timeout_s=10,
    )

    assert result.ok is True
    assert runtime.recorded_args == ("lake", "env", "lean", "--json", "Foo/Bar.lean")


def test_run_lean_json_includes_threads_flag_when_configured(tmp_path: Path) -> None:
    runtime = _RecordingRuntime(
        backend_config=LeanCommandBackendConfig(lean_json_threads=4),
        toolchain_config=ToolchainConfig(),
    )

    result = runtime.run_lean_json(
        project_root=tmp_path,
        rel_file="Foo/Bar.lean",
        timeout_s=10,
    )

    assert result.ok is True
    assert runtime.recorded_args == (
        "lake",
        "env",
        "lean",
        "--json",
        "-j",
        "4",
        "Foo/Bar.lean",
    )
