"""build_base service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...backends.lean import CommandResult, LeanCommandRuntime
from ...backends.lean.path import TargetResolver
from ...config import ToolkitConfig
from ...contracts.build_base import BuildWorkspaceRequest, BuildWorkspaceResponse
from ...core.services import BuildBaseService
from ...tool_audit import audit_stage, get_current_audit_recorder


@dataclass(slots=True)
class BuildBaseServiceImpl(BuildBaseService):
    config: ToolkitConfig
    runtime: LeanCommandRuntime
    resolver: TargetResolver

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        runtime: LeanCommandRuntime | None = None,
        resolver: TargetResolver | None = None,
    ):
        self.config = config
        self.runtime = runtime or LeanCommandRuntime(
            backend_config=config.backends.lean_command,
            toolchain_config=config.toolchain,
        )
        self.resolver = resolver or TargetResolver()

    def run_workspace(self, req: BuildWorkspaceRequest) -> BuildWorkspaceResponse:
        with audit_stage("resolve_targets"):
            project_root = self._resolve_project_root(req.project_root)
            clean_first = (
                req.clean_first
                if req.clean_first is not None
                else self.config.build_base.default_clean_first
            )
            timeout_seconds = (
                req.timeout_seconds
                if req.timeout_seconds is not None
                else self.config.build_base.default_timeout_seconds
            )
            jobs = (
                req.jobs
                if req.jobs is not None
                else (
                    self.config.build_base.default_jobs
                    if self.config.build_base.default_jobs is not None
                    else self.config.backends.lean_command.lake_build_jobs
                )
            )

            normalized_targets: tuple[str, ...]
            if req.targets is None:
                normalized_targets = tuple()
            else:
                resolved = self.resolver.resolve(
                    project_root=project_root,
                    targets=req.targets,
                )
                normalized_targets = resolved.module_dots()
            recorder = get_current_audit_recorder()
            if recorder is not None:
                recorder.set_attr("targets", list(normalized_targets))

        facet = (req.target_facet or "").strip() or None
        if facet is not None and not normalized_targets:
            return BuildWorkspaceResponse(
                success=False,
                error_message="target_facet requires explicit targets",
                project_root=str(project_root),
                targets=tuple(),
                target_facet=facet,
                jobs=jobs,
                executed_commands=tuple(),
                returncode=2,
                timed_out=False,
                stdout="",
                stderr="",
            )

        executed_commands: list[tuple[str, ...]] = []
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        if clean_first:
            with audit_stage("clean"):
                clean_result = self.runtime.run_lake_clean(
                    project_root=project_root,
                    timeout_s=timeout_seconds,
                )
            executed_commands.append(clean_result.args)
            if clean_result.stdout:
                stdout_chunks.append(clean_result.stdout.rstrip())
            if clean_result.stderr:
                stderr_chunks.append(clean_result.stderr.rstrip())
            if not clean_result.ok:
                return self._response_from_result(
                    project_root=project_root,
                    targets=normalized_targets,
                    target_facet=facet,
                    jobs=jobs,
                    executed_commands=tuple(executed_commands),
                    stdout_chunks=stdout_chunks,
                    stderr_chunks=stderr_chunks,
                    result=clean_result,
                    stage="clean",
                )

        with audit_stage("build"):
            build_result = self.runtime.run_lake_build(
                project_root=project_root,
                module_targets=normalized_targets,
                target_facet=facet,
                timeout_s=timeout_seconds,
                jobs=jobs,
            )
        executed_commands.append(build_result.args)
        if build_result.stdout:
            stdout_chunks.append(build_result.stdout.rstrip())
        if build_result.stderr:
            stderr_chunks.append(build_result.stderr.rstrip())
        return self._response_from_result(
            project_root=project_root,
            targets=normalized_targets,
            target_facet=facet,
            jobs=jobs,
            executed_commands=tuple(executed_commands),
            stdout_chunks=stdout_chunks,
            stderr_chunks=stderr_chunks,
            result=build_result,
            stage="build",
        )

    def _resolve_project_root(self, project_root: str | None) -> Path:
        raw = (project_root or self.config.server.default_project_root or "").strip()
        if not raw:
            raise ValueError("project_root is required")
        root = Path(raw).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"project_root is not a directory: {root}")
        return root

    def _response_from_result(
        self,
        *,
        project_root: Path,
        targets: tuple[str, ...],
        target_facet: str | None,
        jobs: int | None,
        executed_commands: tuple[tuple[str, ...], ...],
        stdout_chunks: list[str],
        stderr_chunks: list[str],
        result: CommandResult,
        stage: str,
    ) -> BuildWorkspaceResponse:
        error_message: str | None = None
        if not result.ok:
            if result.timed_out:
                error_message = f"{stage} command timed out"
            else:
                error_message = f"{stage} command failed with return code {result.returncode}"
        return BuildWorkspaceResponse(
            success=result.ok,
            error_message=error_message,
            project_root=str(project_root),
            targets=targets,
            target_facet=target_facet,
            jobs=jobs,
            executed_commands=executed_commands,
            returncode=result.returncode,
            timed_out=result.timed_out,
            stdout="\n\n".join(chunk for chunk in stdout_chunks if chunk),
            stderr="\n\n".join(chunk for chunk in stderr_chunks if chunk),
        )
