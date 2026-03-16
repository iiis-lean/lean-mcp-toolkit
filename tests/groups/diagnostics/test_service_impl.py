from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.diagnostics import BuildRequest, LintRequest
from lean_mcp_toolkit.groups.diagnostics.service_impl import DiagnosticsServiceImpl
from lean_mcp_toolkit.groups.diagnostics.runtime import CommandResult


@dataclass(slots=True)
class _FakeRuntime:
    def run_lake_build(self, *, project_root: Path, module_targets: tuple[str, ...], timeout_s: int | None, jobs: int | None) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = timeout_s
        _ = jobs
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json(self, *, project_root: Path, rel_file: str, timeout_s: int | None) -> CommandResult:
        _ = project_root
        _ = timeout_s
        if rel_file == "A/Bad.lean":
            msg = '{"severity":"error","pos":{"line":1,"column":0},"data":"bad proof","kind":"typeMismatch","fileName":"A.Bad"}'
            return CommandResult(args=("lean", "--json", rel_file), returncode=1, stdout=msg, stderr="")
        msg = '{"severity":"warning","pos":{"line":1,"column":0},"data":"declaration uses sorry","kind":"hasSorry","fileName":"A.Good"}'
        return CommandResult(args=("lean", "--json", rel_file), returncode=0, stdout=msg, stderr="")


@dataclass(slots=True)
class _FailBuildDepsRuntime:
    lean_calls: int = 0

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        timeout_s: int | None,
        jobs: int | None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = timeout_s
        _ = jobs
        return CommandResult(
            args=("lake", "build"),
            returncode=1,
            stdout="",
            stderr="build deps failed",
        )

    def run_lean_json(
        self, *, project_root: Path, rel_file: str, timeout_s: int | None
    ) -> CommandResult:
        _ = project_root
        _ = rel_file
        _ = timeout_s
        self.lean_calls += 1
        return CommandResult(args=("lean", "--json"), returncode=0, stdout="", stderr="")


@dataclass(slots=True)
class _FailEmitRuntime:
    lake_calls: int = 0

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        timeout_s: int | None,
        jobs: int | None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = timeout_s
        _ = jobs
        self.lake_calls += 1
        if self.lake_calls >= 1:
            return CommandResult(
                args=("lake", "build"),
                returncode=2,
                stdout="",
                stderr="emit artifacts failed",
            )
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json(
        self, *, project_root: Path, rel_file: str, timeout_s: int | None
    ) -> CommandResult:
        _ = project_root
        _ = rel_file
        _ = timeout_s
        msg = '{"severity":"warning","pos":{"line":1,"column":0},"data":"warn only","kind":"[anonymous]","fileName":"A.Good"}'
        return CommandResult(args=("lean", "--json"), returncode=0, stdout=msg, stderr="")



def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")



def test_run_build_and_lint(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Bad.lean", "theorem t : True := by\n  exact False.elim ?h\n")
    _write(tmp_path / "A" / "Good.lean", "theorem g : True := by\n  sorry\n")

    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=_FakeRuntime())

    build_resp = svc.run_build(BuildRequest.from_dict({"targets": ["A/Bad.lean", "A/Good.lean"]}))
    assert build_resp.success is False
    assert build_resp.failed_stage == "diagnostics"
    assert len(build_resp.files) == 2

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Bad.lean", "A/Good.lean"]}))
    assert lint_resp.success is False
    assert len(lint_resp.checks) == 3
    no_sorry = lint_resp.checks[0]
    assert no_sorry.check_id == "no_sorry"
    assert lint_resp.checks[1].check_id == "no_axiom_decl"
    assert lint_resp.checks[1].success is False
    assert "not implemented" in lint_resp.checks[1].message
    assert lint_resp.checks[2].check_id == "axiom_usage"
    assert lint_resp.checks[2].success is False
    assert "not implemented" in lint_resp.checks[2].message


def test_run_build_build_deps_failure_short_circuit(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Good.lean", "theorem g : True := by\n  trivial\n")

    runtime = _FailBuildDepsRuntime()
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    resp = svc.run_build(
        BuildRequest.from_dict({"targets": ["A/Good.lean"], "build_deps": True})
    )
    assert resp.success is False
    assert resp.failed_stage == "build_deps"
    assert resp.stage_error_message is not None
    assert len(resp.files) == 0
    assert runtime.lean_calls == 0


def test_run_build_emit_failure_returns_stage_error(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Good.lean", "theorem g : True := by\n  trivial\n")

    runtime = _FailEmitRuntime()
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    resp = svc.run_build(
        BuildRequest.from_dict(
            {"targets": ["A/Good.lean"], "build_deps": False, "emit_artifacts": True}
        )
    )
    assert resp.success is False
    assert resp.failed_stage == "emit_artifacts"
    assert resp.stage_error_message is not None
    assert len(resp.files) == 1


def test_run_lint_no_sorry_fails_on_build_stage_failure(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Good.lean", "theorem g : True := by\n  trivial\n")

    runtime = _FailBuildDepsRuntime()
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {"default_build_deps": True},
        }
    )
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    no_sorry = svc.run_lint_no_sorry(
        LintRequest.from_dict({"targets": ["A/Good.lean"]})
    )
    assert no_sorry.success is False
    assert len(no_sorry.sorries) == 0
