from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time

from lean_mcp_toolkit.backends.declarations import DeclarationsBackendResponse
from lean_mcp_toolkit.backends.lean import CommandResult
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.diagnostics import (
    AxiomAuditResult,
    BuildRequest,
    FileRequest,
    LintRequest,
)
from lean_mcp_toolkit.groups.diagnostics.service_impl import DiagnosticsServiceImpl


@dataclass(slots=True)
class _FakeRuntime:
    lake_calls: list[tuple[tuple[str, ...], str | None]] = None

    def __post_init__(self) -> None:
        if self.lake_calls is None:
            self.lake_calls = []

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = timeout_s
        _ = jobs
        self.lake_calls.append((module_targets, target_facet))
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json(self, *, project_root: Path, rel_file: str, timeout_s: int | None) -> CommandResult:
        _ = project_root
        _ = timeout_s
        if rel_file == "A/Bad.lean":
            msg = '{"severity":"error","pos":{"line":1,"column":0},"data":"bad proof","kind":"typeMismatch","fileName":"A.Bad"}'
            return CommandResult(args=("lean", "--json", rel_file), returncode=1, stdout=msg, stderr="")
        msg = '{"severity":"warning","pos":{"line":1,"column":0},"data":"declaration uses sorry","kind":"hasSorry","fileName":"A.Good"}'
        return CommandResult(args=("lean", "--json", rel_file), returncode=0, stdout=msg, stderr="")


@dataclass(slots=True, frozen=True)
class _FakeDecl:
    full_name: str
    kind: str = "theorem"


@dataclass(slots=True)
class _FakeDeclBackend:
    by_module: dict[str, tuple[_FakeDecl, ...]]
    extract_calls: list[str] = None

    def __post_init__(self) -> None:
        if self.extract_calls is None:
            self.extract_calls = []

    def extract(self, req):
        self.extract_calls.append(req.target_dot)
        decls = self.by_module.get(req.target_dot, tuple())
        return DeclarationsBackendResponse(
            success=True,
            error_message=None,
            declarations=decls,
            messages=tuple(),
            sorries=tuple(),
        )

    def extract_batch(self, reqs):
        return tuple(self.extract(req) for req in reqs)

@dataclass(slots=True)
class _AxiomProbeRuntime:
    axiom_map: dict[str, tuple[str, ...]]
    probed_decls: list[str] = None
    lake_calls: list[tuple[tuple[str, ...], str | None]] = None
    multiline_axiom_output: bool = False

    def __post_init__(self) -> None:
        if self.probed_decls is None:
            self.probed_decls = []
        if self.lake_calls is None:
            self.lake_calls = []

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = timeout_s
        _ = jobs
        self.lake_calls.append((module_targets, target_facet))
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json(self, *, project_root: Path, rel_file: str, timeout_s: int | None) -> CommandResult:
        _ = timeout_s
        abs_file = (project_root / rel_file).resolve()
        try:
            text = abs_file.read_text(encoding="utf-8")
        except Exception:
            return CommandResult(args=("lean", "--json", rel_file), returncode=1, stdout="", stderr="probe read failed")

        messages: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line.startswith("#print axioms "):
                continue
            decl = line[len("#print axioms ") :].strip()
            self.probed_decls.append(decl)
            axioms = self.axiom_map.get(decl)
            if axioms is None:
                continue
            if len(axioms) == 0:
                payload = f"'{decl}' does not depend on any axioms"
            else:
                joined = ",\n ".join(axioms) if self.multiline_axiom_output else ", ".join(axioms)
                payload = f"'{decl}' depends on axioms: [{joined}]"
            messages.append(
                json.dumps(
                    {
                        "severity": "information",
                        "pos": {"line": 1, "column": 0},
                        "data": payload,
                        "kind": "[anonymous]",
                        "fileName": rel_file,
                    }
                )
            )
        return CommandResult(
            args=("lean", "--json", rel_file),
            returncode=0,
            stdout="\n".join(messages),
            stderr="",
        )


@dataclass(slots=True)
class _FailBuildDepsRuntime:
    lean_calls: int = 0
    last_target_facet: str | None = None

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = timeout_s
        _ = jobs
        self.last_target_facet = target_facet
        return CommandResult(
            args=("lake", "build", "A.Good:deps" if target_facet == "deps" else "A.Good"),
            returncode=1,
            stdout=(
                "✖ [1/2] Building A.Dep\n"
                "error: A/Dep.lean:3:5: dependency failed\n"
                "Some required targets logged failures:\n"
                "- A.Dep"
            ),
            stderr="error: build failed",
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
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = target_facet
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


@dataclass(slots=True)
class _BatchOnlyRuntime:
    batch_calls: int = 0

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = target_facet
        _ = timeout_s
        _ = jobs
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json(self, *, project_root: Path, rel_file: str, timeout_s: int | None) -> CommandResult:
        _ = project_root
        _ = rel_file
        _ = timeout_s
        raise AssertionError("service should use run_lean_json_batch when available")

    def run_lean_json_batch(
        self,
        *,
        project_root: Path,
        rel_files: tuple[str, ...],
        timeout_s: int | None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        _ = project_root
        _ = timeout_s
        self.batch_calls += 1
        out: list[tuple[str, CommandResult]] = []
        for rel_file in rel_files:
            msg = (
                '{"severity":"warning","pos":{"line":1,"column":0},'
                '"data":"warn only","kind":"[anonymous]","fileName":"A.Good"}'
            )
            out.append(
                (
                    rel_file,
                    CommandResult(
                        args=("lean", "--json", rel_file),
                        returncode=0,
                        stdout=msg,
                        stderr="",
                    ),
                )
            )
        return tuple(out)


@dataclass(slots=True)
class _CoordinatedRuntime:
    sleep_s: float = 0.2
    lake_calls: int = 0
    batch_calls: int = 0
    active_calls: int = 0
    max_active_calls: int = 0
    _lock: threading.Lock = None

    def __post_init__(self) -> None:
        if self._lock is None:
            self._lock = threading.Lock()

    def _enter(self) -> None:
        with self._lock:
            self.active_calls += 1
            if self.active_calls > self.max_active_calls:
                self.max_active_calls = self.active_calls

    def _exit(self) -> None:
        with self._lock:
            self.active_calls -= 1

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = target_facet
        _ = timeout_s
        _ = jobs
        self._enter()
        try:
            time.sleep(self.sleep_s)
            self.lake_calls += 1
            return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")
        finally:
            self._exit()

    def run_lean_json_batch(
        self,
        *,
        project_root: Path,
        rel_files: tuple[str, ...],
        timeout_s: int | None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        _ = project_root
        _ = timeout_s
        self._enter()
        try:
            time.sleep(self.sleep_s)
            self.batch_calls += 1
            out: list[tuple[str, CommandResult]] = []
            for rel_file in rel_files:
                abs_file = (project_root / rel_file).resolve()
                try:
                    text = abs_file.read_text(encoding="utf-8")
                except Exception:
                    text = ""
                messages: list[str] = []
                for raw in text.splitlines():
                    line = raw.strip()
                    if not line.startswith("#print axioms "):
                        continue
                    decl = line[len("#print axioms ") :].strip()
                    messages.append(
                        json.dumps(
                            {
                                "severity": "information",
                                "pos": {"line": 1, "column": 0},
                                "data": f"'{decl}' does not depend on any axioms",
                                "kind": "[anonymous]",
                                "fileName": rel_file,
                            }
                        )
                    )
                out.append(
                    (
                        rel_file,
                        CommandResult(
                            args=("lean", "--json", rel_file),
                            returncode=0,
                            stdout="\n".join(messages),
                            stderr="",
                        ),
                    )
                )
            return tuple(out)
        finally:
            self._exit()

    def run_lean_json(self, *, project_root: Path, rel_file: str, timeout_s: int | None) -> CommandResult:
        _ = project_root
        _ = rel_file
        _ = timeout_s
        raise AssertionError("batch runner should be used in coordination tests")


@dataclass(slots=True)
class _SlowBuildRuntime:
    sleep_s: float = 1.2
    lake_calls: int = 0
    batch_calls: int = 0

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None = None,
    ) -> CommandResult:
        _ = project_root
        _ = module_targets
        _ = target_facet
        _ = timeout_s
        _ = jobs
        self.lake_calls += 1
        time.sleep(self.sleep_s)
        return CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr="")

    def run_lean_json_batch(
        self,
        *,
        project_root: Path,
        rel_files: tuple[str, ...],
        timeout_s: int | None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        _ = project_root
        _ = timeout_s
        self.batch_calls += 1
        return tuple(
            (
                rel_file,
                CommandResult(
                    args=("lean", "--json", rel_file),
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            )
            for rel_file in rel_files
        )


@dataclass(slots=True)
class _FakeLspDiagResult:
    diagnostics: list[dict]


@dataclass(slots=True)
class _FakeLspClient:
    def open_file(self, rel_path: str) -> None:
        _ = rel_path

    def get_diagnostics(self, rel_path: str, inactivity_timeout: float = 15.0):
        _ = inactivity_timeout
        if rel_path == "A/File.lean":
            return _FakeLspDiagResult(
                diagnostics=[
                    {
                        "severity": 2,
                        "message": "declaration uses sorry",
                        "kind": "hasSorry",
                        "range": {
                            "start": {"line": 1, "character": 2},
                            "end": {"line": 1, "character": 7},
                        },
                    }
                ]
            )
        return _FakeLspDiagResult(
            diagnostics=[
                {
                    "severity": 1,
                    "message": "type mismatch",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 4},
                    },
                }
            ]
        )


@dataclass(slots=True)
class _FakeLspClientManager:
    client: _FakeLspClient

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client



def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")



def test_run_build_and_lint(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Bad.lean", "theorem t : True := by\n  exact False.elim ?h\n")
    _write(tmp_path / "A" / "Good.lean", "theorem g : True := by\n  sorry\n")

    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=_FakeRuntime(),
        declarations_backends={"lean_interact": _FakeDeclBackend(by_module={})},
    )

    build_resp = svc.run_build(BuildRequest.from_dict({"targets": ["A/Bad.lean", "A/Good.lean"]}))
    assert build_resp.success is False
    assert build_resp.failed_stage == "diagnostics"
    assert len(build_resp.files) == 2

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Bad.lean", "A/Good.lean"]}))
    assert lint_resp.success is False
    assert len(lint_resp.checks) == 2
    no_sorry = lint_resp.checks[0]
    assert no_sorry.check_id == "no_sorry"
    assert lint_resp.checks[1].check_id == "axiom_audit"
    assert lint_resp.checks[1].success is True
    assert "eligible" in lint_resp.checks[1].message


def test_run_lint_requires_explicit_targets(tmp_path: Path) -> None:
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=_FakeRuntime(),
        declarations_backends={"lean_interact": _FakeDeclBackend(by_module={})},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({}))
    assert lint_resp.success is False
    assert len(lint_resp.checks) == 2
    assert lint_resp.checks[0].check_id == "no_sorry"
    assert lint_resp.checks[0].success is False
    assert "requires explicit" in lint_resp.checks[0].message
    assert lint_resp.checks[1].check_id == "axiom_audit"
    assert lint_resp.checks[1].success is False
    assert "requires explicit" in lint_resp.checks[1].message


def test_run_lint_subchecks_require_explicit_targets(tmp_path: Path) -> None:
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=_FakeRuntime(),
        declarations_backends={"lean_interact": _FakeDeclBackend(by_module={})},
    )

    no_sorry = svc.run_lint_no_sorry(LintRequest.from_dict({}))
    assert no_sorry.success is False
    assert "requires explicit" in no_sorry.message
    assert no_sorry.sorries == tuple()

    axiom_audit = svc.run_lint_axiom_audit(LintRequest.from_dict({}))
    assert axiom_audit.success is False
    assert "requires explicit" in axiom_audit.message
    assert axiom_audit.unresolved == tuple()


def test_run_file_with_lsp_diagnostics(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "File.lean", "theorem t : True := by\n  sorry\n")
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=_FakeRuntime(),
        lsp_client_manager=_FakeLspClientManager(client=_FakeLspClient()),
    )

    resp = svc.run_file(
        FileRequest.from_dict(
            {
                "file_path": "A/File.lean",
                "include_content": True,
                "context_lines": 1,
            }
        )
    )
    assert resp.success is True
    assert resp.file == "A.File"
    assert resp.warning_count == 1
    assert resp.sorry_count == 1
    assert len(resp.items) == 1
    assert resp.items[0].content is not None


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
    assert "A/Dep.lean:3:5" in resp.stage_error_message
    assert "A.Good:deps" in resp.stage_error_message
    assert len(resp.files) == 0
    assert runtime.lean_calls == 0
    assert runtime.last_target_facet == "deps"


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
    assert "A/Dep.lean:3:5" in no_sorry.message


def test_run_build_uses_batch_runner_when_available(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "F1.lean", "theorem t1 : True := by\n  trivial\n")
    _write(tmp_path / "A" / "F2.lean", "theorem t2 : True := by\n  trivial\n")

    runtime = _BatchOnlyRuntime()
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    resp = svc.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["A/F1.lean", "A/F2.lean"],
                "build_deps": False,
                "emit_artifacts": False,
            }
        )
    )
    assert resp.success is True
    assert runtime.batch_calls == 1
    assert tuple(file_diag.file for file_diag in resp.files) == ("A.F1", "A.F2")


def test_run_lint_axiom_audit_detects_risky_axioms(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Good.lean", "theorem t : True := by\n  trivial\n")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(axiom_map={"A.Good.t": ("MyAxiom",)})
    backend = _FakeDeclBackend(by_module={"A.Good": (_FakeDecl(full_name="A.Good.t"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Good.lean"]}))
    assert lint_resp.success is False
    assert len(lint_resp.checks) == 1
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.check_id == "axiom_audit"
    assert check.success is False
    issues = check.usage_issues
    assert len(issues) == 1
    assert issues[0].declaration == "A.Good.t"
    assert issues[0].risky_axioms == ("MyAxiom",)


def test_run_lint_axiom_audit_filters_sorry_ax_by_default(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Good.lean", "theorem t : True := by\n  trivial\n")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(axiom_map={"A.Good.t": ("sorryAx",)})
    backend = _FakeDeclBackend(by_module={"A.Good": (_FakeDecl(full_name="A.Good.t"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Good.lean"]}))
    assert lint_resp.success is True
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.check_id == "axiom_audit"
    assert check.success is True
    assert check.usage_issues == tuple()
    assert check.unresolved == tuple()


def test_run_lint_axiom_audit_normalizes_root_prefixed_declaration_names(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Pkg.lean", "abbrev adjacentDiff := 1\n")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(axiom_map={"adjacentDiff": tuple()})
    backend = _FakeDeclBackend(by_module={"A.Pkg": (_FakeDecl(full_name="_root_.adjacentDiff"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
    assert lint_resp.success is True
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.success is True
    assert check.unresolved == tuple()
    assert runtime.probed_decls == ["A.Pkg.adjacentDiff", "_root_.adjacentDiff", "adjacentDiff"]


def test_run_lint_axiom_audit_retries_probe_candidates_in_batches(tmp_path: Path) -> None:
    _write(
        tmp_path / "A" / "Pkg.lean",
        "\n".join(
            [
                "theorem ok : True := by",
                "  trivial",
                "abbrev adjacentDiff := 1",
                "",
            ]
        ),
    )
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(
        axiom_map={
            "A.Pkg.ok": tuple(),
            "A.Pkg.adjacentDiff": tuple(),
        }
    )
    backend = _FakeDeclBackend(
        by_module={
            "A.Pkg": (
                _FakeDecl(full_name="A.Pkg.ok"),
                _FakeDecl(full_name="_root_.adjacentDiff"),
            )
        }
    )
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
    assert lint_resp.success is True
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.success is True
    assert check.unresolved == tuple()
    assert runtime.probed_decls == [
        "A.Pkg.ok",
        "A.Pkg.adjacentDiff",
    ]
    assert runtime.lake_calls == [(("A.Pkg",), "leanArts")]


def test_run_lint_axiom_audit_rejects_top_level_alias_exports(tmp_path: Path) -> None:
    _write(
        tmp_path / "A" / "Pkg.lean",
        "\n".join(
            [
                "namespace A.Pkg",
                "alias A.Summary.foo := foo",
                "end A.Pkg",
                "",
            ]
        ),
    )
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(axiom_map={})
    backend = _FakeDeclBackend(by_module={"A.Pkg": tuple()})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
    assert lint_resp.success is False
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.success is False
    assert len(check.unresolved) == 1
    assert check.unresolved[0].declaration == "foo"
    assert "top-level alias declarations are disallowed" in check.unresolved[0].reason


def test_run_lint_axiom_audit_skips_files_without_top_level_declarations(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Empty.lean", "import Mathlib\n\nnamespace A.Empty\n\nend A.Empty\n")
    _write(tmp_path / "A" / "Full.lean", "theorem t : True := by\n  trivial\n")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(axiom_map={"A.Full.t": tuple()})
    backend = _FakeDeclBackend(by_module={"A.Full": (_FakeDecl(full_name="A.Full.t"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Empty.lean", "A/Full.lean"]}))
    assert lint_resp.success is True
    assert backend.extract_calls == ["A.Full"]


def test_run_lint_axiom_audit_parses_multiline_axiom_reports(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Pkg.lean", "theorem t : True := by\n  trivial\n")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    runtime = _AxiomProbeRuntime(
        axiom_map={"A.Pkg.t": ("propext", "MyAxiom", "Quot.sound")},
        multiline_axiom_output=True,
    )
    backend = _FakeDeclBackend(by_module={"A.Pkg": (_FakeDecl(full_name="A.Pkg.t"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    lint_resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
    assert lint_resp.success is False
    check = lint_resp.checks[0]
    assert isinstance(check, AxiomAuditResult)
    assert check.success is False
    assert check.unresolved == tuple()
    assert len(check.usage_issues) == 1
    assert check.usage_issues[0].declaration == "A.Pkg.t"
    assert check.usage_issues[0].risky_axioms == ("MyAxiom",)


def test_run_lint_no_sorry_singleflights_same_target(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Pkg.lean", "theorem t : True := by\n  trivial\n")
    runtime = _CoordinatedRuntime()
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    barrier = threading.Barrier(3)
    results: list[bool] = []
    errors: list[str] = []

    def _worker() -> None:
        try:
            barrier.wait()
            resp = svc.run_lint_no_sorry(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
            results.append(resp.success)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(str(exc))

    threads = [threading.Thread(target=_worker) for _ in range(3)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert errors == []
    assert results == [True, True, True]
    assert runtime.lake_calls == 1
    assert runtime.batch_calls == 1
    assert runtime.max_active_calls == 1


def test_run_lint_and_no_sorry_serialize_same_target_family(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Pkg.lean", "theorem t : True := by\n  trivial\n")
    runtime = _CoordinatedRuntime()
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "diagnostics": {
                "default_enabled_checks": ["no_sorry", "axiom_audit"],
                "default_build_deps": False,
            },
        }
    )
    backend = _FakeDeclBackend(by_module={"A.Pkg": (_FakeDecl(full_name="A.Pkg.t"),)})
    svc = DiagnosticsServiceImpl(
        config=cfg,
        runtime=runtime,
        declarations_backends={"lean_interact": backend},
    )

    barrier = threading.Barrier(2)
    errors: list[str] = []

    def _run_lint() -> None:
        try:
            barrier.wait()
            resp = svc.run_lint(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
            assert resp.success is True
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(str(exc))

    def _run_no_sorry() -> None:
        try:
            barrier.wait()
            resp = svc.run_lint_no_sorry(LintRequest.from_dict({"targets": ["A/Pkg.lean"]}))
            assert resp.success is True
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(str(exc))

    t1 = threading.Thread(target=_run_lint)
    t2 = threading.Thread(target=_run_no_sorry)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
    assert runtime.max_active_calls == 1


def test_run_lint_no_sorry_uses_request_deadline_across_stages(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Pkg.lean", "theorem t : True := by\n  trivial\n")
    runtime = _SlowBuildRuntime()
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DiagnosticsServiceImpl(config=cfg, runtime=runtime)

    resp = svc.run_lint_no_sorry(
        LintRequest.from_dict(
            {
                "targets": ["A/Pkg.lean"],
                "timeout_seconds": 1,
            }
        )
    )

    assert resp.success is False
    assert "timed out" in resp.message
    assert runtime.lake_calls == 1
    assert runtime.batch_calls == 0
