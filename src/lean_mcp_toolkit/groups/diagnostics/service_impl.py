"""Diagnostics service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from ...config import ToolkitConfig
from ...contracts.diagnostics import (
    BuildRequest,
    BuildResponse,
    CheckResult,
    DiagnosticItem,
    FileDiagnostics,
    LintRequest,
    LintResponse,
    NoSorryResult,
)
from ...core.services import DiagnosticsService
from .parsing.context_extractor import ContextExtractor
from .parsing.diagnostic_parser import LeanDiagnosticParser
from .paths.lean_path import LeanPath
from .paths.target_resolver import TargetResolver
from .runtime.command_models import CommandResult
from .runtime.command_runtime import LeanCommandRuntime


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


@dataclass(slots=True)
class DiagnosticsServiceImpl(DiagnosticsService):
    """Default diagnostics service implementation."""

    config: ToolkitConfig
    runtime: LeanCommandRuntime
    resolver: TargetResolver
    parser: LeanDiagnosticParser
    context_extractor: ContextExtractor

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        runtime: LeanCommandRuntime | None = None,
        resolver: TargetResolver | None = None,
        parser: LeanDiagnosticParser | None = None,
        context_extractor: ContextExtractor | None = None,
    ):
        self.config = config
        self.runtime = runtime or LeanCommandRuntime(
            diagnostics_config=config.diagnostics,
            toolchain_config=config.toolchain,
        )
        self.resolver = resolver or TargetResolver()
        self.parser = parser or LeanDiagnosticParser()
        self.context_extractor = context_extractor or ContextExtractor()

    def run_build(self, req: BuildRequest) -> BuildResponse:
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
            deps_result = self.runtime.run_lake_build(
                project_root=resolved.project_root_abs,
                module_targets=resolved.module_dots(),
                timeout_s=options.timeout_seconds,
                jobs=self.config.diagnostics.lake_build_jobs,
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

        for module in resolved.modules:
            file_results.append(
                self._run_file_diagnostics(
                    module=module,
                    options=options,
                )
            )

        if options.emit_artifacts:
            success_modules = tuple(
                file_result.file for file_result in file_results if file_result.success
            )
            if success_modules:
                emit_result = self.runtime.run_lake_build(
                    project_root=resolved.project_root_abs,
                    module_targets=success_modules,
                    timeout_s=options.timeout_seconds,
                    jobs=self.config.diagnostics.lake_build_jobs,
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

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        lint_options = self._effective_lint_options(req)
        build_req = BuildRequest(
            project_root=str(lint_options.project_root),
            targets=req.targets,
            build_deps=self.config.diagnostics.default_build_deps,
            emit_artifacts=False,
            include_content=lint_options.include_content,
            context_lines=lint_options.context_lines,
            timeout_seconds=lint_options.timeout_seconds,
        )
        build_resp = self.run_build(build_req)
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
        enabled = req.enabled_checks or self.config.diagnostics.default_enabled_checks
        checks: list[CheckResult | NoSorryResult] = []

        for check_id in enabled:
            cid = check_id.strip()
            if not cid:
                continue
            if cid == "no_sorry":
                checks.append(self.run_lint_no_sorry(req))
            else:
                checks.append(
                    CheckResult(
                        check_id=cid,
                        success=False,
                        message=f"not implemented lint check: {cid}",
                    )
                )

        success = all(check.success for check in checks)
        return LintResponse(success=success, checks=tuple(checks))

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

    def _resolve_project_root(self, project_root: str | None) -> Path:
        root = (
            project_root
            or self.config.server.default_project_root
            or os.getcwd()
        )
        return Path(root).expanduser().resolve()

    def _run_file_diagnostics(
        self,
        *,
        module: LeanPath,
        options: EffectiveBuildOptions,
    ) -> FileDiagnostics:
        rel_file = module.to_rel_file()
        cmd_result = self.runtime.run_lean_json(
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
            parts.append(f"stderr={stderr.splitlines()[0]}")
        elif stdout:
            parts.append(f"stdout={stdout.splitlines()[0]}")

        return " | ".join(parts)
