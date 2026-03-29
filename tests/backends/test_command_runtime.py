from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

from lean_mcp_toolkit.backends.lean.command_runtime import LeanCommandRuntime
from lean_mcp_toolkit.config import LeanCommandBackendConfig, ToolchainConfig


def _runtime() -> LeanCommandRuntime:
    return LeanCommandRuntime(
        backend_config=LeanCommandBackendConfig(),
        toolchain_config=ToolchainConfig(),
    )


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
