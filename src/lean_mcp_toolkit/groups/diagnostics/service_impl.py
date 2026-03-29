"""Diagnostics service implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import os
from pathlib import Path
import re
import threading
import time
import uuid

from ...backends.declarations import (
    DeclarationsBackend,
    DeclarationsBackendRequest,
    DeclarationsBackendResponse,
    LeanInteractDeclarationsBackend,
    NativeDeclarationsBackend,
)
from ...backends.lean import CommandResult, LeanCommandRuntime
from ...backends.lean.path import LeanPath, TargetResolver
from ...backends.lsp import LeanLSPClientManager
from ...config import ToolkitConfig
from ...contracts.diagnostics import (
    AxiomAuditResult,
    AxiomDeclaredItem,
    AxiomUsageIssue,
    AxiomUsageUnresolved,
    BuildRequest,
    BuildResponse,
    CheckResult,
    DiagnosticItem,
    FileRequest,
    FileResponse,
    FileDiagnostics,
    LintRequest,
    LintResponse,
    NoSorryResult,
    Position,
)
from ...core.services import DiagnosticsService
from .parsing.context_extractor import ContextExtractor
from .parsing.diagnostic_parser import LeanDiagnosticParser

_AXIOM_DEPENDS_RE = re.compile(
    r"^'(?P<decl>.+?)'\s+depends on axioms:\s*\[(?P<axioms>.*?)\]\s*$",
    re.DOTALL,
)
_AXIOM_NONE_RE = re.compile(r"^'(?P<decl>.+?)'\s+does not depend on any axioms\s*$")
_TOP_LEVEL_ALIAS_RE = re.compile(
    r"^alias\s+(?P<target>.+?)\s*:=\s*(?P<export>[A-Za-z0-9_'.]+)\s*$"
)
_TOP_LEVEL_DECL_HEAD_RE = re.compile(
    r"^(?P<kw>theorem|lemma|def|abbrev|instance|axiom|constant|structure|class|inductive)\b"
)


@dataclass(slots=True, frozen=True)
class EffectiveBuildOptions:
    project_root: Path
    build_deps: bool
    emit_artifacts: bool
    include_content: bool
    context_lines: int
    timeout_seconds: int | None


@dataclass(slots=True, frozen=True)
class EffectiveLintOptions:
    project_root: Path
    include_content: bool
    context_lines: int
    timeout_seconds: int | None


@dataclass(slots=True, frozen=True)
class AxiomProbeJob:
    module_dot: str
    probe_rel_file: str
    probe_abs_file: Path
    declarations: tuple[str, ...]
    probe_names: tuple[str, ...]


@dataclass(slots=True)
class _InflightCall:
    event: threading.Event = field(default_factory=threading.Event)
    result: object | None = None
    error: BaseException | None = None


@dataclass(slots=True, frozen=True)
class _RequestBudget:
    deadline_monotonic: float | None

    def remaining_timeout_seconds(self) -> int | None:
        if self.deadline_monotonic is None:
            return None
        remaining = self.deadline_monotonic - time.monotonic()
        if remaining <= 0:
            return 0
        return max(1, int(remaining + 0.999))

    def remaining_wait_seconds(self) -> float | None:
        if self.deadline_monotonic is None:
            return None
        return max(0.0, self.deadline_monotonic - time.monotonic())


class _RequestTimeoutError(TimeoutError):
    pass


@dataclass(slots=True)
class DiagnosticsServiceImpl(DiagnosticsService):
    """Default diagnostics service implementation."""

    config: ToolkitConfig
    runtime: LeanCommandRuntime
    resolver: TargetResolver
    parser: LeanDiagnosticParser
    context_extractor: ContextExtractor
    declarations_backends: dict[str, DeclarationsBackend]
    lsp_client_manager: LeanLSPClientManager
    _coord_lock: threading.Lock = field(init=False, repr=False)
    _scope_locks: dict[tuple[str, tuple[str, ...]], threading.Lock] = field(
        init=False,
        repr=False,
    )
    _inflight_calls: dict[tuple[str, tuple[str, tuple[str, ...]], tuple[object, ...]], _InflightCall] = field(
        init=False,
        repr=False,
    )

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        runtime: LeanCommandRuntime | None = None,
        resolver: TargetResolver | None = None,
        parser: LeanDiagnosticParser | None = None,
        context_extractor: ContextExtractor | None = None,
        declarations_backends: dict[str, DeclarationsBackend] | None = None,
        lsp_client_manager: LeanLSPClientManager | None = None,
    ):
        self.config = config
        self.runtime = runtime or LeanCommandRuntime(
            backend_config=config.backends.lean_command,
            toolchain_config=config.toolchain,
        )
        self.resolver = resolver or TargetResolver()
        self.parser = parser or LeanDiagnosticParser()
        self.context_extractor = context_extractor or ContextExtractor()
        self.declarations_backends = declarations_backends or {
            "lean_interact": LeanInteractDeclarationsBackend(
                toolchain_config=config.toolchain,
                backend_config=config.backends.lean_interact,
            ),
            "native": NativeDeclarationsBackend(),
        }
        self.lsp_client_manager = lsp_client_manager or LeanLSPClientManager(
            backend_config=config.backends.lsp
        )
        self._coord_lock = threading.Lock()
        self._scope_locks = {}
        self._inflight_calls = {}

    def run_build(self, req: BuildRequest) -> BuildResponse:
        budget = self._build_request_budget(req.timeout_seconds)
        try:
            return self._run_with_target_coordination(
                op_name="build",
                scope=self._coordination_scope(
                    project_root=req.project_root,
                    targets=req.targets,
                ),
                signature=(
                    bool(req.build_deps)
                    if req.build_deps is not None
                    else bool(self.config.diagnostics.default_build_deps),
                    bool(req.emit_artifacts)
                    if req.emit_artifacts is not None
                    else bool(self.config.diagnostics.default_emit_artifacts),
                    bool(req.include_content)
                    if req.include_content is not None
                    else bool(self.config.diagnostics.default_include_content),
                    int(req.context_lines)
                    if req.context_lines is not None
                    else int(self.config.diagnostics.default_context_lines),
                    req.timeout_seconds,
                ),
                budget=budget,
                func=lambda: self._run_build_impl(req, budget),
            )
        except _RequestTimeoutError as exc:
            return BuildResponse(
                success=False,
                files=tuple(),
                failed_stage="request_timeout",
                stage_error_message=str(exc),
            )

    def _run_build_impl(self, req: BuildRequest, budget: _RequestBudget) -> BuildResponse:
        options = self._effective_build_options(req)
        resolved = self.resolver.resolve(
            project_root=options.project_root,
            targets=list(req.targets) if req.targets is not None else None,
        )
        if not resolved.modules:
            return BuildResponse(
                success=True,
                files=tuple(),
                failed_stage=None,
                stage_error_message=None,
            )

        file_results: list[FileDiagnostics] = []

        if options.build_deps:
            deps_result = self._runtime_run_lake_build(
                project_root=resolved.project_root_abs,
                module_targets=resolved.module_dots(),
                target_facet="deps",
                timeout_s=self._remaining_timeout_seconds(
                    budget,
                    operation="build_deps",
                ),
                jobs=self.config.backends.lean_command.lake_build_jobs,
                deadline_monotonic=budget.deadline_monotonic,
            )
            if not deps_result.ok:
                return BuildResponse(
                    success=False,
                    files=tuple(),
                    failed_stage="build_deps",
                    stage_error_message=self._format_command_failure_message(
                        stage="build_deps",
                        cmd_result=deps_result,
                    ),
                )

        batch_results = self._run_lean_json_batch(
            project_root=options.project_root,
            modules=resolved.modules,
            timeout_seconds=self._remaining_timeout_seconds(
                budget,
                operation="diagnostics",
            ),
            deadline_monotonic=budget.deadline_monotonic,
        )
        result_map = {rel_file: cmd_result for rel_file, cmd_result in batch_results}
        for module in resolved.modules:
            rel_file = module.to_rel_file()
            cmd_result = result_map.get(rel_file)
            if cmd_result is None:
                cmd_result = self._missing_batch_result(rel_file=rel_file)
            file_results.append(
                self._run_file_diagnostics(
                    module=module,
                    options=options,
                    cmd_result=cmd_result,
                )
            )

        if options.emit_artifacts:
            success_modules = tuple(
                file_result.file for file_result in file_results if file_result.success
            )
            if success_modules:
                emit_result = self._runtime_run_lake_build(
                    project_root=resolved.project_root_abs,
                    module_targets=success_modules,
                    target_facet="leanArts",
                    timeout_s=self._remaining_timeout_seconds(
                        budget,
                        operation="emit_artifacts",
                    ),
                    jobs=self.config.backends.lean_command.lake_build_jobs,
                    deadline_monotonic=budget.deadline_monotonic,
                )
                if not emit_result.ok:
                    return BuildResponse(
                        success=False,
                        files=tuple(file_results),
                        failed_stage="emit_artifacts",
                        stage_error_message=self._format_command_failure_message(
                            stage="emit_artifacts",
                            cmd_result=emit_result,
                        ),
                    )

        success = all(item.success for item in file_results)
        return BuildResponse(
            success=success,
            files=tuple(file_results),
            failed_stage=(None if success else "diagnostics"),
            stage_error_message=None,
        )

    def run_file(self, req: FileRequest) -> FileResponse:
        module: LeanPath | None = None
        try:
            project_root = self._resolve_project_root(req.project_root)
            resolved = self.resolver.resolve(
                project_root=project_root,
                targets=[req.file_path],
            )
            if len(resolved.modules) != 1:
                raise ValueError("diagnostics.file expects exactly one Lean file target")
            module = resolved.modules[0]

            include_content = (
                req.include_content
                if req.include_content is not None
                else self.config.diagnostics.default_include_content
            )
            context_lines = (
                req.context_lines
                if req.context_lines is not None
                else self.config.diagnostics.default_context_lines
            )
            timeout_seconds = (
                req.timeout_seconds
                if req.timeout_seconds is not None
                else self.config.diagnostics.default_timeout_seconds
            )

            client = self.lsp_client_manager.get_client(project_root)
            rel_file = module.to_rel_file()
            client.open_file(rel_file)

            inactivity_timeout = float(
                timeout_seconds
                if timeout_seconds is not None
                else self.config.backends.lsp.diagnostics_timeout_seconds
            )
            raw_result = client.get_diagnostics(
                rel_file,
                inactivity_timeout=inactivity_timeout,
            )
            raw_items = self._extract_lsp_diagnostics_list(raw_result)
            items = [self._map_lsp_diagnostic_item(item, fallback_file=module.dot) for item in raw_items]

            if include_content:
                items = self._attach_content(
                    module=module,
                    items=items,
                    project_root=project_root,
                    context_lines=context_lines,
                )

            error_count = 0
            warning_count = 0
            info_count = 0
            sorry_count = 0
            for item in items:
                sev = (item.severity or "").strip().lower()
                if sev == "error":
                    error_count += 1
                elif sev == "warning":
                    warning_count += 1
                else:
                    info_count += 1
                if self._is_sorry(item):
                    sorry_count += 1

            return FileResponse(
                success=error_count == 0,
                error_message=None,
                file=module.dot,
                items=tuple(items),
                total_items=len(items),
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
                sorry_count=sorry_count,
            )
        except Exception as exc:
            return FileResponse(
                success=False,
                error_message=str(exc),
                file=(module.dot if module is not None else ""),
                items=tuple(),
                total_items=0,
                error_count=0,
                warning_count=0,
                info_count=0,
                sorry_count=0,
            )

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        budget = self._build_request_budget(req.timeout_seconds)
        try:
            return self._run_with_target_coordination(
                op_name="no_sorry",
                scope=self._coordination_scope(
                    project_root=req.project_root,
                    targets=req.targets,
                ),
                signature=(
                    bool(req.include_content)
                    if req.include_content is not None
                    else bool(self.config.diagnostics.default_include_content),
                    int(req.context_lines)
                    if req.context_lines is not None
                    else int(self.config.diagnostics.default_context_lines),
                    req.timeout_seconds,
                ),
                budget=budget,
                func=lambda: self._run_lint_no_sorry_impl(req, budget),
            )
        except _RequestTimeoutError as exc:
            return NoSorryResult(
                check_id="no_sorry",
                success=False,
                message=str(exc),
                sorries=tuple(),
            )

    def _run_lint_no_sorry_impl(self, req: LintRequest, budget: _RequestBudget) -> NoSorryResult:
        if not req.targets:
            return NoSorryResult(
                check_id="no_sorry",
                success=False,
                message=self._lint_targets_required_message(),
                sorries=tuple(),
            )
        lint_options = self._effective_lint_options(req)
        build_req = BuildRequest(
            project_root=str(lint_options.project_root),
            targets=req.targets,
            build_deps=self.config.diagnostics.default_build_deps,
            emit_artifacts=False,
            include_content=lint_options.include_content,
            context_lines=lint_options.context_lines,
            timeout_seconds=self._remaining_timeout_seconds(
                budget,
                operation="no_sorry",
            ),
        )
        build_resp = self._run_build_impl(build_req, budget)
        if build_resp.failed_stage in {"build_deps", "emit_artifacts"}:
            stage_msg = build_resp.stage_error_message or f"stage failure: {build_resp.failed_stage}"
            return NoSorryResult(
                check_id="no_sorry",
                success=False,
                message=stage_msg,
                sorries=tuple(),
            )

        sorries: list[DiagnosticItem] = []
        for file_result in build_resp.files:
            for item in file_result.items:
                if self._is_sorry(item):
                    sorries.append(item)

        success = len(sorries) == 0
        message = "no sorry found" if success else f"found {len(sorries)} sorry diagnostics"
        return NoSorryResult(
            check_id="no_sorry",
            success=success,
            message=message,
            sorries=tuple(sorries),
        )

    def run_lint(self, req: LintRequest) -> LintResponse:
        enabled = tuple(req.enabled_checks or self.config.diagnostics.default_enabled_checks)
        budget = self._build_request_budget(req.timeout_seconds)
        try:
            return self._run_with_target_coordination(
                op_name="lint",
                scope=self._coordination_scope(
                    project_root=req.project_root,
                    targets=req.targets,
                ),
                signature=(
                    enabled,
                    bool(req.include_content)
                    if req.include_content is not None
                    else bool(self.config.diagnostics.default_include_content),
                    int(req.context_lines)
                    if req.context_lines is not None
                    else int(self.config.diagnostics.default_context_lines),
                    req.timeout_seconds,
                ),
                budget=budget,
                func=lambda: self._run_lint_impl(req, enabled, budget),
            )
        except _RequestTimeoutError as exc:
            return LintResponse(
                success=False,
                checks=(
                    CheckResult(
                        check_id="request_timeout",
                        success=False,
                        message=str(exc),
                    ),
                ),
            )

    def _run_lint_impl(
        self,
        req: LintRequest,
        enabled: tuple[str, ...],
        budget: _RequestBudget,
    ) -> LintResponse:
        checks: list[CheckResult] = []

        for check_id in enabled:
            cid = check_id.strip()
            if not cid:
                continue
            try:
                if cid == "no_sorry":
                    checks.append(self._run_lint_no_sorry_impl(req, budget))
                elif cid == "axiom_audit":
                    checks.append(self._run_lint_axiom_audit_impl(req, budget))
                else:
                    checks.append(
                        CheckResult(
                            check_id=cid,
                            success=False,
                            message=f"not implemented lint check: {cid}",
                        )
                    )
            except _RequestTimeoutError as exc:
                checks.append(
                    CheckResult(
                        check_id=cid,
                        success=False,
                        message=str(exc),
                    )
                )
                break

        success = all(check.success for check in checks)
        return LintResponse(success=success, checks=tuple(checks))

    def run_lint_axiom_audit(self, req: LintRequest) -> AxiomAuditResult:
        budget = self._build_request_budget(req.timeout_seconds)
        try:
            return self._run_with_target_coordination(
                op_name="axiom_audit",
                scope=self._coordination_scope(
                    project_root=req.project_root,
                    targets=req.targets,
                ),
                signature=(
                    bool(req.include_content)
                    if req.include_content is not None
                    else bool(self.config.diagnostics.default_include_content),
                    int(req.context_lines)
                    if req.context_lines is not None
                    else int(self.config.diagnostics.default_context_lines),
                    req.timeout_seconds,
                ),
                budget=budget,
                func=lambda: self._run_lint_axiom_audit_impl(req, budget),
            )
        except _RequestTimeoutError as exc:
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=False,
                message=str(exc),
                declared_axioms=tuple(),
                usage_issues=tuple(),
                unresolved=tuple(),
            )

    def _run_lint_axiom_audit_impl(self, req: LintRequest, budget: _RequestBudget) -> AxiomAuditResult:
        if not req.targets:
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=False,
                message=self._lint_targets_required_message(),
                declared_axioms=tuple(),
                usage_issues=tuple(),
                unresolved=tuple(),
            )
        options = self._effective_lint_options(req)
        resolved = self.resolver.resolve(
            project_root=options.project_root,
            targets=list(req.targets) if req.targets is not None else None,
        )
        if not resolved.modules:
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=True,
                message="no target files to check",
                declared_axioms=tuple(),
                usage_issues=tuple(),
                unresolved=tuple(),
            )

        artifact_result = self._runtime_run_lake_build(
            project_root=resolved.project_root_abs,
            module_targets=resolved.module_dots(),
            target_facet="leanArts",
            timeout_s=self._remaining_timeout_seconds(
                budget,
                operation="axiom_audit.prepare_target",
            ),
            jobs=self.config.backends.lean_command.lake_build_jobs,
            deadline_monotonic=budget.deadline_monotonic,
        )
        if not artifact_result.ok:
            msg = self._format_command_failure_message(
                stage="axiom_audit.prepare_target",
                cmd_result=artifact_result,
            )
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=False,
                message=msg,
                declared_axioms=tuple(),
                usage_issues=tuple(),
                unresolved=tuple(),
            )

        backend = self._resolve_declarations_backend()
        if backend is None:
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=False,
                message=(
                    f"unsupported declarations backend: "
                    f"{self.config.declarations.default_backend}"
                ),
                declared_axioms=tuple(),
                usage_issues=tuple(),
                unresolved=tuple(),
            )

        declared_axioms: list[AxiomDeclaredItem] = []
        unresolved: list[AxiomUsageUnresolved] = []
        modules_by_dot = {module.dot: module for module in resolved.modules}
        pending_probe_candidates: dict[tuple[str, str], tuple[str, ...]] = {}
        decl_kind_filter = {
            item.strip().lower()
            for item in self.config.diagnostics.axiom_audit_decl_kinds
            if item.strip()
        }
        modules_for_extract = tuple(
            module
            for module in resolved.modules
            if self._module_may_contain_auditable_declarations(
                module=module,
                project_root=options.project_root,
            )
        )
        backend_reqs = tuple(
            DeclarationsBackendRequest(
                project_root=options.project_root,
                target_dot=module.dot,
                timeout_seconds=options.timeout_seconds,
            )
            for module in modules_for_extract
        )
        declarations_resps = backend.extract_batch(backend_reqs)
        declarations_resp_by_dot = {
            module.dot: resp
            for module, resp in zip(modules_for_extract, declarations_resps)
        }

        for module in resolved.modules:
            alias_exports = self._find_top_level_alias_exports(
                module=module,
                project_root=options.project_root,
            )
            for export_name in alias_exports:
                unresolved.append(
                    AxiomUsageUnresolved(
                        fileName=module.dot,
                        declaration=export_name,
                        reason=(
                            "top-level alias declarations are disallowed in audited files; "
                            "replace alias with an explicit abbrev/def/theorem wrapper"
                        ),
                    )
                )
            declarations_resp = declarations_resp_by_dot.get(
                module.dot,
                DeclarationsBackendResponse(
                    success=True,
                    error_message=None,
                    declarations=tuple(),
                    messages=tuple(),
                    sorries=tuple(),
                ),
            )
            if not declarations_resp.success and declarations_resp.error_message:
                unresolved.append(
                    AxiomUsageUnresolved(
                        fileName=module.dot,
                        declaration=None,
                        reason=declarations_resp.error_message,
                    )
                )

            if declarations_resp.declarations:
                declared_axioms.extend(
                    self._collect_declared_axioms(
                        module=module,
                        declarations=declarations_resp.declarations,
                        project_root=options.project_root,
                        include_content=options.include_content,
                        context_lines=options.context_lines,
                        decl_kind_filter=decl_kind_filter,
                    )
                )
            declarations = self._collect_checkable_declarations(
                declarations=declarations_resp.declarations,
                decl_kind_filter=decl_kind_filter,
            )
            if declarations:
                for decl in declarations:
                    pending_probe_candidates[(module.dot, decl)] = (
                        self._candidate_declaration_names(
                            module=module,
                            declaration=decl,
                        )
                    )

        if not pending_probe_candidates:
            success = self._axiom_audit_success(
                declared_axioms=declared_axioms,
                usage_issues=tuple(),
                unresolved=unresolved,
            )
            message = (
                "no declarations eligible for usage audit"
                if success
                else self._build_axiom_audit_message(
                    declared_axioms=declared_axioms,
                    usage_issues=tuple(),
                    unresolved=unresolved,
                )
            )
            return AxiomAuditResult(
                check_id="axiom_audit",
                success=success,
                message=message,
                declared_axioms=tuple(declared_axioms),
                usage_issues=tuple(),
                unresolved=tuple(unresolved),
            )

        allowed_axioms = {
            item.strip()
            for item in self.config.diagnostics.axiom_audit_allowed_axioms
            if item.strip()
        }
        include_sorry_ax = self.config.diagnostics.axiom_audit_include_sorry_ax
        usage_issues: list[AxiomUsageIssue] = []
        max_rounds = max(
            (len(candidates) for candidates in pending_probe_candidates.values()),
            default=0,
        )
        last_failure_reason: dict[tuple[str, str], str] = {}

        for round_index in range(max_rounds):
            jobs = self._build_axiom_probe_round_jobs(
                project_root=options.project_root,
                modules_by_dot=modules_by_dot,
                pending_probe_candidates=pending_probe_candidates,
                round_index=round_index,
            )
            if not jobs:
                continue

            rel_files = tuple(job.probe_rel_file for job in jobs)
            try:
                batch_results = self._run_lean_json_rel_files_batch(
                    project_root=options.project_root,
                    rel_files=rel_files,
                    timeout_seconds=options.timeout_seconds,
                )
                result_map = {rel_file: cmd for rel_file, cmd in batch_results}

                for job in jobs:
                    cmd_result = result_map.get(job.probe_rel_file)
                    if cmd_result is None:
                        for decl in job.declarations:
                            last_failure_reason[(job.module_dot, decl)] = "missing probe batch result"
                        continue

                    axiom_map = self._parse_axiom_usage_from_result(
                        cmd_result=cmd_result,
                        project_root=options.project_root,
                        fallback_module=LeanPath.from_dot(job.module_dot),
                    )
                    unresolved_reason = (
                        self._format_command_failure_message(
                            stage="axiom_audit.probe",
                            cmd_result=cmd_result,
                        )
                        if cmd_result.returncode != 0
                        else "axiom report not found in probe output"
                    )

                    for decl, probe_name in zip(job.declarations, job.probe_names, strict=True):
                        key = (job.module_dot, decl)
                        axioms = self._resolve_axioms_for_probe_name(
                            probe_name=probe_name,
                            axiom_map=axiom_map,
                        )
                        if axioms is None:
                            last_failure_reason[key] = (
                                f"{unresolved_reason}; candidate={probe_name}"
                            )
                            continue

                        pending_probe_candidates.pop(key, None)
                        last_failure_reason.pop(key, None)
                        risky_axioms = [ax for ax in axioms if ax not in allowed_axioms]
                        if not include_sorry_ax:
                            risky_axioms = [ax for ax in risky_axioms if ax != "sorryAx"]
                        if risky_axioms:
                            usage_issues.append(
                                AxiomUsageIssue(
                                    fileName=job.module_dot,
                                    declaration=decl,
                                    risky_axioms=tuple(risky_axioms),
                                )
                            )
            finally:
                self._cleanup_probe_files(tuple(job.probe_abs_file for job in jobs))

        for (module_dot, decl), candidates in pending_probe_candidates.items():
            tried = ", ".join(candidates)
            reason = last_failure_reason.get(
                (module_dot, decl),
                "axiom report not found in probe output",
            )
            unresolved.append(
                AxiomUsageUnresolved(
                    fileName=module_dot,
                    declaration=decl,
                    reason=(
                        f"failed to resolve declaration via probe candidates: "
                        f"[{tried}]; last error: {reason}"
                    ),
                )
            )

        success = self._axiom_audit_success(
            declared_axioms=declared_axioms,
            usage_issues=usage_issues,
            unresolved=unresolved,
        )
        if success:
            message = "no declared axioms or risky axiom usage found"
        else:
            message = self._build_axiom_audit_message(
                declared_axioms=declared_axioms,
                usage_issues=usage_issues,
                unresolved=unresolved,
            )

        return AxiomAuditResult(
            check_id="axiom_audit",
            success=success,
            message=message,
            declared_axioms=tuple(declared_axioms),
            usage_issues=tuple(usage_issues),
            unresolved=tuple(unresolved),
        )

    def _coordination_scope(
        self,
        *,
        project_root: str | None,
        targets: tuple[str, ...] | None,
    ) -> tuple[str, tuple[str, ...]] | None:
        if not targets:
            return None
        try:
            resolved_project_root = self._resolve_project_root(project_root)
            resolved = self.resolver.resolve(
                project_root=resolved_project_root,
                targets=list(targets),
            )
        except Exception:
            return None
        rel_files = tuple(module.to_rel_file() for module in resolved.modules)
        if not rel_files:
            return None
        return (str(resolved_project_root), rel_files)

    def _run_with_target_coordination(
        self,
        *,
        op_name: str,
        scope: tuple[str, tuple[str, ...]] | None,
        signature: tuple[object, ...],
        budget: _RequestBudget,
        func,
    ):
        if scope is None:
            self._ensure_budget_active(budget, operation=op_name)
            return func()

        inflight_key = (op_name, scope, signature)
        with self._coord_lock:
            entry = self._inflight_calls.get(inflight_key)
            if entry is None:
                entry = _InflightCall()
                self._inflight_calls[inflight_key] = entry
                is_owner = True
            else:
                is_owner = False
            scope_lock = self._scope_locks.setdefault(scope, threading.Lock())

        if not is_owner:
            wait_s = budget.remaining_wait_seconds()
            if wait_s is not None and wait_s <= 0:
                raise _RequestTimeoutError(f"{op_name} request timed out")
            finished = entry.event.wait(wait_s)
            if not finished:
                raise _RequestTimeoutError(f"{op_name} request timed out")
            if entry.error is not None:
                raise entry.error
            return entry.result

        try:
            with scope_lock:
                self._ensure_budget_active(budget, operation=op_name)
                result = func()
        except BaseException as exc:
            entry.error = exc
            raise
        else:
            entry.result = result
            return result
        finally:
            entry.event.set()
            with self._coord_lock:
                self._inflight_calls.pop(inflight_key, None)

    def _resolve_declarations_backend(self) -> DeclarationsBackend | None:
        return self.declarations_backends.get(self.config.declarations.default_backend)

    def _collect_checkable_declarations(
        self,
        *,
        declarations: tuple[object, ...],
        decl_kind_filter: set[str],
    ) -> tuple[str, ...]:
        names: list[str] = []
        for decl in declarations:
            full_name = str(
                getattr(decl, "full_name", None)
                or getattr(decl, "name", None)
                or ""
            ).strip()
            if not full_name:
                continue
            kind = self._decl_kind(decl)
            if kind in decl_kind_filter:
                continue
            names.append(full_name)
        return tuple(dict.fromkeys(names))

    def _collect_declared_axioms(
        self,
        *,
        module: LeanPath,
        declarations: tuple[object, ...],
        project_root: Path,
        include_content: bool,
        context_lines: int,
        decl_kind_filter: set[str],
    ) -> list[AxiomDeclaredItem]:
        source_text: str | None = None
        if include_content:
            try:
                source_text = module.to_abs_file(project_root).read_text(encoding="utf-8")
            except Exception:
                source_text = None

        out: list[AxiomDeclaredItem] = []
        for decl in declarations:
            kind = self._decl_kind(decl)
            if kind not in decl_kind_filter:
                continue
            start_pos, end_pos = self._decl_range_positions(decl)
            full_name = str(
                getattr(decl, "full_name", None)
                or getattr(decl, "name", None)
                or ""
            ).strip() or None
            snippet: str | None = None
            if (
                source_text is not None
                and start_pos is not None
                and end_pos is not None
            ):
                snippet = self.context_extractor.extract(
                    source_text=source_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    context_lines=max(0, context_lines),
                )
            out.append(
                AxiomDeclaredItem(
                    fileName=module.dot,
                    declaration=full_name,
                    kind=kind or None,
                    pos=start_pos,
                    endPos=end_pos,
                    content=snippet,
                )
            )
        return out

    @staticmethod
    def _decl_kind(decl: object) -> str:
        return str(getattr(decl, "kind", None) or "").strip().lower()

    @staticmethod
    def _decl_range_positions(decl: object) -> tuple[Position | None, Position | None]:
        rng = getattr(decl, "range", None)
        if rng is None:
            return None, None
        start = getattr(rng, "start", None)
        finish = getattr(rng, "finish", None)
        if start is None or finish is None:
            return None, None
        try:
            start_pos = Position(line=int(start.line), column=int(start.column))
            end_pos = Position(line=int(finish.line), column=int(finish.column))
        except Exception:
            return None, None
        return start_pos, end_pos

    def _axiom_audit_success(
        self,
        *,
        declared_axioms: list[AxiomDeclaredItem],
        usage_issues: list[AxiomUsageIssue] | tuple[AxiomUsageIssue, ...],
        unresolved: list[AxiomUsageUnresolved] | tuple[AxiomUsageUnresolved, ...],
    ) -> bool:
        if declared_axioms:
            return False
        if usage_issues:
            return False
        if unresolved and self.config.diagnostics.axiom_audit_fail_on_unresolved:
            return False
        return True

    def _build_axiom_audit_message(
        self,
        *,
        declared_axioms: list[AxiomDeclaredItem],
        usage_issues: list[AxiomUsageIssue] | tuple[AxiomUsageIssue, ...],
        unresolved: list[AxiomUsageUnresolved] | tuple[AxiomUsageUnresolved, ...],
    ) -> str:
        parts: list[str] = []
        if declared_axioms:
            parts.append(f"found {len(declared_axioms)} declared axioms")
        if usage_issues:
            parts.append(f"found {len(usage_issues)} risky axiom usage item(s)")
        if unresolved:
            parts.append(f"{len(unresolved)} declaration(s) unresolved")
        if not parts:
            return "no declared axioms or risky axiom usage found"
        return "; ".join(parts)

    def _write_axiom_probe_file(
        self,
        *,
        project_root: Path,
        module: LeanPath,
        declarations: tuple[str, ...],
        probe_names: tuple[str, ...],
    ) -> AxiomProbeJob:
        probe_abs = (project_root / f"_mcp_axprobe_{uuid.uuid4().hex}.lean").resolve()
        lines = [f"import {module.dot}", ""]
        lines.extend(f"#print axioms {probe_name}" for probe_name in probe_names)
        probe_abs.write_text("\n".join(lines) + "\n", encoding="utf-8")
        probe_rel = probe_abs.relative_to(project_root).as_posix()
        return AxiomProbeJob(
            module_dot=module.dot,
            probe_rel_file=probe_rel,
            probe_abs_file=probe_abs,
            declarations=declarations,
            probe_names=probe_names,
        )

    def _parse_axiom_usage_from_result(
        self,
        *,
        cmd_result: CommandResult,
        project_root: Path,
        fallback_module: LeanPath,
    ) -> dict[str, list[str]]:
        combined_text = "\n".join([cmd_result.stdout, cmd_result.stderr]).strip()
        items = self.parser.parse_text(
            text=combined_text,
            project_root=project_root,
            fallback_module=fallback_module,
        )
        parsed: dict[str, list[str]] = {}
        for item in items:
            if item.severity.strip().lower() != "information":
                continue
            msg = item.data.strip()
            if not msg:
                continue

            match_dep = _AXIOM_DEPENDS_RE.match(msg)
            if match_dep is not None:
                decl = match_dep.group("decl").strip()
                payload = match_dep.group("axioms").strip()
                axioms = [part.strip() for part in payload.split(",") if part.strip()] if payload else []
                parsed[decl] = axioms
                continue

            match_none = _AXIOM_NONE_RE.match(msg)
            if match_none is not None:
                decl = match_none.group("decl").strip()
                parsed[decl] = []

        return parsed

    def _resolve_axioms_for_probe_name(
        self,
        *,
        probe_name: str,
        axiom_map: dict[str, list[str]],
    ) -> list[str] | None:
        normalized = self._normalize_declaration_name(probe_name)
        direct = axiom_map.get(probe_name)
        if direct is None and normalized != probe_name:
            direct = axiom_map.get(normalized)
        if direct is not None:
            return direct

        short = normalized.split(".")[-1]
        candidates = [
            axioms
            for name, axioms in axiom_map.items()
            if self._normalize_declaration_name(name) == normalized
            or name == short
            or name.endswith(f".{short}")
        ]
        if len(candidates) == 1:
            return candidates[0]
        return None

    @staticmethod
    def _normalize_declaration_name(name: str) -> str:
        normalized = name.strip()
        while normalized.startswith("_root_."):
            normalized = normalized[len("_root_.") :]
        return normalized

    def _candidate_declaration_names(
        self,
        *,
        module: LeanPath,
        declaration: str,
    ) -> tuple[str, ...]:
        raw = declaration.strip()
        normalized = self._normalize_declaration_name(raw)
        short = normalized.split(".")[-1].strip() if normalized else ""

        candidates: list[str] = []
        module_qualified = f"{module.dot}.{short}" if short else ""
        for item in (module_qualified, raw, normalized):
            if item and item not in candidates:
                candidates.append(item)
        return tuple(candidates)

    def _find_top_level_alias_exports(
        self,
        *,
        module: LeanPath,
        project_root: Path,
    ) -> tuple[str, ...]:
        try:
            text = module.to_abs_file(project_root).read_text(encoding="utf-8")
        except Exception:
            return tuple()
        names: list[str] = []
        for raw in text.splitlines():
            line = raw.strip("\n")
            match = _TOP_LEVEL_ALIAS_RE.match(line)
            if match is None:
                continue
            export_name = match.group("export").strip()
            if export_name and export_name not in names:
                names.append(export_name)
        return tuple(names)

    def _module_may_contain_auditable_declarations(
        self,
        *,
        module: LeanPath,
        project_root: Path,
    ) -> bool:
        abs_file = (project_root / module.to_rel_file()).resolve()
        try:
            text = abs_file.read_text(encoding="utf-8")
        except Exception:
            return True
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("--") or stripped.startswith("/-"):
                continue
            if raw[:1].isspace():
                continue
            if _TOP_LEVEL_ALIAS_RE.match(stripped) is not None:
                return True
            if _TOP_LEVEL_DECL_HEAD_RE.match(stripped) is not None:
                return True
        return False

    def _build_axiom_probe_round_jobs(
        self,
        *,
        project_root: Path,
        modules_by_dot: dict[str, LeanPath],
        pending_probe_candidates: dict[tuple[str, str], tuple[str, ...]],
        round_index: int,
    ) -> list[AxiomProbeJob]:
        grouped: dict[str, list[tuple[str, str]]] = {}
        for (module_dot, declaration), candidates in pending_probe_candidates.items():
            if round_index >= len(candidates):
                continue
            grouped.setdefault(module_dot, []).append((declaration, candidates[round_index]))

        jobs: list[AxiomProbeJob] = []
        for module_dot, entries in grouped.items():
            module = modules_by_dot.get(module_dot)
            if module is None:
                continue
            declarations = tuple(declaration for declaration, _ in entries)
            probe_names = tuple(probe_name for _, probe_name in entries)
            jobs.append(
                self._write_axiom_probe_file(
                    project_root=project_root,
                    module=module,
                    declarations=declarations,
                    probe_names=probe_names,
                )
            )
        return jobs

    def _effective_build_options(self, req: BuildRequest) -> EffectiveBuildOptions:
        project_root = self._resolve_project_root(req.project_root)
        return EffectiveBuildOptions(
            project_root=project_root,
            build_deps=(
                req.build_deps
                if req.build_deps is not None
                else self.config.diagnostics.default_build_deps
            ),
            emit_artifacts=(
                req.emit_artifacts
                if req.emit_artifacts is not None
                else self.config.diagnostics.default_emit_artifacts
            ),
            include_content=(
                req.include_content
                if req.include_content is not None
                else self.config.diagnostics.default_include_content
            ),
            context_lines=(
                req.context_lines
                if req.context_lines is not None
                else self.config.diagnostics.default_context_lines
            ),
            timeout_seconds=(
                req.timeout_seconds
                if req.timeout_seconds is not None
                else self.config.diagnostics.default_timeout_seconds
            ),
        )

    def _effective_lint_options(self, req: LintRequest) -> EffectiveLintOptions:
        project_root = self._resolve_project_root(req.project_root)
        return EffectiveLintOptions(
            project_root=project_root,
            include_content=(
                req.include_content
                if req.include_content is not None
                else self.config.diagnostics.default_include_content
            ),
            context_lines=(
                req.context_lines
                if req.context_lines is not None
                else self.config.diagnostics.default_context_lines
            ),
            timeout_seconds=(
                req.timeout_seconds
                if req.timeout_seconds is not None
                else self.config.diagnostics.default_timeout_seconds
            ),
        )

    @staticmethod
    def _lint_targets_required_message() -> str:
        return "lint requires explicit Lean file or directory targets; targets must be non-empty"

    def _resolve_project_root(self, project_root: str | None) -> Path:
        root = project_root or self.config.server.default_project_root or os.getcwd()
        return Path(root).expanduser().resolve()

    def _run_file_diagnostics(
        self,
        *,
        module: LeanPath,
        options: EffectiveBuildOptions,
        cmd_result: CommandResult | None = None,
    ) -> FileDiagnostics:
        if cmd_result is None:
            rel_file = module.to_rel_file()
            cmd_result = self._runtime_run_lean_json(
                project_root=options.project_root,
                rel_file=rel_file,
                timeout_s=options.timeout_seconds,
            )

        combined_text = "\n".join([cmd_result.stdout, cmd_result.stderr]).strip()
        items = list(
            self.parser.parse_text(
                text=combined_text,
                project_root=options.project_root,
                fallback_module=module,
            )
        )

        if cmd_result.returncode != 0 and not any(self._is_error(it) for it in items):
            items.append(
                self._command_failure_item(
                    module=module,
                    stage="lean_json",
                    cmd_result=cmd_result,
                )
            )

        if options.include_content:
            items = self._attach_content(
                module=module,
                items=items,
                project_root=options.project_root,
                context_lines=options.context_lines,
            )

        success = not any(self._is_error(item) for item in items)
        return FileDiagnostics(file=module.dot, success=success, items=tuple(items))

    def _run_lean_json_batch(
        self,
        *,
        project_root: Path,
        modules: tuple[LeanPath, ...],
        timeout_seconds: int | None,
        deadline_monotonic: float | None = None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        rel_files = tuple(module.to_rel_file() for module in modules)
        return self._run_lean_json_rel_files_batch(
            project_root=project_root,
            rel_files=rel_files,
            timeout_seconds=timeout_seconds,
            deadline_monotonic=deadline_monotonic,
        )

    def _run_lean_json_rel_files_batch(
        self,
        *,
        project_root: Path,
        rel_files: tuple[str, ...],
        timeout_seconds: int | None,
        deadline_monotonic: float | None = None,
    ) -> tuple[tuple[str, CommandResult], ...]:
        batch_runner = getattr(self.runtime, "run_lean_json_batch", None)
        if callable(batch_runner):
            return tuple(
                self._call_runtime_method(
                    batch_runner,
                    project_root=project_root,
                    rel_files=rel_files,
                    timeout_s=timeout_seconds,
                    deadline_monotonic=deadline_monotonic,
                )
            )

        return tuple(
            (
                rel_file,
                self._runtime_run_lean_json(
                    project_root=project_root,
                    rel_file=rel_file,
                    timeout_s=timeout_seconds,
                    deadline_monotonic=deadline_monotonic,
                ),
            )
            for rel_file in rel_files
        )

    @staticmethod
    def _build_request_budget(timeout_seconds: int | None) -> _RequestBudget:
        if timeout_seconds is None:
            return _RequestBudget(deadline_monotonic=None)
        return _RequestBudget(deadline_monotonic=time.monotonic() + max(0, timeout_seconds))

    @staticmethod
    def _ensure_budget_active(budget: _RequestBudget, *, operation: str) -> None:
        remaining = budget.remaining_wait_seconds()
        if remaining is not None and remaining <= 0:
            raise _RequestTimeoutError(f"{operation} request timed out")

    def _remaining_timeout_seconds(
        self,
        budget: _RequestBudget,
        *,
        operation: str,
    ) -> int | None:
        self._ensure_budget_active(budget, operation=operation)
        return budget.remaining_timeout_seconds()

    def _runtime_run_lake_build(self, **kwargs) -> CommandResult:
        return self._call_runtime_method(self.runtime.run_lake_build, **kwargs)

    def _runtime_run_lean_json(self, **kwargs) -> CommandResult:
        return self._call_runtime_method(self.runtime.run_lean_json, **kwargs)

    @staticmethod
    def _call_runtime_method(method, **kwargs):
        params = inspect.signature(method).parameters
        filtered = {key: value for key, value in kwargs.items() if key in params}
        return method(**filtered)

    def _missing_batch_result(self, *, rel_file: str) -> CommandResult:
        return CommandResult(
            args=("lean", "--json", rel_file),
            returncode=70,
            stdout="",
            stderr="missing batch diagnostic result",
            timed_out=False,
        )

    def _cleanup_probe_files(self, paths: tuple[Path, ...]) -> None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                continue

    @staticmethod
    def _extract_lsp_diagnostics_list(result: object) -> list[dict]:
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if isinstance(result, dict):
            raw = result.get("diagnostics")
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
            return []
        diagnostics = getattr(result, "diagnostics", None)
        if isinstance(diagnostics, list):
            return [item for item in diagnostics if isinstance(item, dict)]
        return []

    @classmethod
    def _map_lsp_diagnostic_item(
        cls,
        item: dict,
        *,
        fallback_file: str,
    ) -> DiagnosticItem:
        severity = item.get("severity")
        if isinstance(severity, int):
            severity_map = {
                1: "error",
                2: "warning",
                3: "information",
                4: "hint",
            }
            severity_text = severity_map.get(severity, str(severity))
        else:
            severity_text = str(severity or "").strip().lower() or "error"

        file_name = item.get("fileName")
        file_name_text = (
            str(file_name).strip()
            if file_name is not None and str(file_name).strip()
            else fallback_file
        )

        start_pos: Position | None = None
        end_pos: Position | None = None
        raw_range = item.get("fullRange") or item.get("range")
        if isinstance(raw_range, dict):
            raw_start = raw_range.get("start")
            raw_end = raw_range.get("end")
            if isinstance(raw_start, dict):
                try:
                    start_pos = Position(
                        line=int(raw_start.get("line", 0)) + 1,
                        column=int(raw_start.get("character", 0)) + 1,
                    )
                except Exception:
                    start_pos = None
            if isinstance(raw_end, dict):
                try:
                    end_pos = Position(
                        line=int(raw_end.get("line", 0)) + 1,
                        column=int(raw_end.get("character", 0)) + 1,
                    )
                except Exception:
                    end_pos = None

        message = str(item.get("message") or item.get("data") or "")
        kind = item.get("kind")
        kind_text = str(kind).strip() if kind is not None and str(kind).strip() else None
        return DiagnosticItem(
            severity=severity_text,
            pos=start_pos,
            endPos=end_pos,
            kind=kind_text,
            data=message,
            fileName=file_name_text,
            content=None,
        )

    def _attach_content(
        self,
        *,
        module: LeanPath,
        items: list[DiagnosticItem],
        project_root: Path,
        context_lines: int,
    ) -> list[DiagnosticItem]:
        file_path = module.to_abs_file(project_root)
        try:
            source_text = file_path.read_text(encoding="utf-8")
        except Exception:
            return items

        enriched: list[DiagnosticItem] = []
        for item in items:
            if item.pos is None:
                enriched.append(item)
                continue
            snippet = self.context_extractor.extract(
                source_text=source_text,
                start_pos=item.pos,
                end_pos=item.endPos,
                context_lines=max(0, context_lines),
            )
            if snippet is None:
                enriched.append(item)
                continue
            enriched.append(
                DiagnosticItem(
                    severity=item.severity,
                    pos=item.pos,
                    endPos=item.endPos,
                    kind=item.kind,
                    data=item.data,
                    fileName=item.fileName,
                    content=snippet,
                )
            )
        return enriched

    def _is_error(self, item: DiagnosticItem) -> bool:
        return item.severity.strip().lower() == "error"

    def _is_sorry(self, item: DiagnosticItem) -> bool:
        kind = (item.kind or "").strip().lower()
        if kind == "hassorry":
            return True
        data_text = item.data.lower()
        return "sorry" in data_text

    def _command_failure_item(
        self,
        *,
        module: LeanPath,
        stage: str,
        cmd_result: CommandResult,
    ) -> DiagnosticItem:
        return DiagnosticItem(
            severity="error",
            pos=None,
            endPos=None,
            kind="command_failure",
            data=self._format_command_failure_message(stage=stage, cmd_result=cmd_result),
            fileName=module.dot,
            content=None,
        )

    def _format_command_failure_message(self, *, stage: str, cmd_result: CommandResult) -> str:
        parts: list[str] = [
            f"{stage} failed with returncode={cmd_result.returncode}",
            f"command={' '.join(cmd_result.args)}",
        ]
        if cmd_result.timed_out:
            parts.append("timed_out=true")

        stderr = (cmd_result.stderr or "").strip()
        stdout = (cmd_result.stdout or "").strip()

        if stderr:
            parts.append(f"stderr={self._summarize_command_output(stderr)}")
        if stdout:
            parts.append(f"stdout={self._summarize_command_output(stdout)}")

        return " | ".join(parts)

    def _summarize_command_output(self, text: str, *, max_lines: int = 12, max_chars: int = 4000) -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        lines = normalized.splitlines()
        tail = lines[-max_lines:]
        snippet = "\n".join(tail)
        if len(snippet) > max_chars:
            snippet = snippet[-max_chars:]
        if len(lines) > max_lines or len(normalized) > len(snippet):
            snippet = f"...\n{snippet}"
        return snippet
