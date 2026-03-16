"""Diagnostics group plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover - optional runtime dependency

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_diagnostics_build,
    handle_diagnostics_lint,
    handle_diagnostics_lint_no_sorry,
)
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from .factory import create_diagnostics_client, create_diagnostics_service
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
)

_BUILD_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description=(
            "Lean project root directory. If not provided, server default root is used."
        ),
    ),
    ToolParamSpec(
        name="targets",
        type_hint="list[str] | str | null",
        required=False,
        default_value="null (check all default targets)",
        description=(
            "Lean targets to check. Supports Lean dot path (A.B.C), relative .lean file path "
            "(A/B/C.lean), relative directory, or absolute path under project root."
        ),
    ),
    ToolParamSpec(
        name="build_deps",
        type_hint="bool | null",
        required=False,
        default_value="diagnostics.default_build_deps",
        description=(
            "Whether to run `lake build` for targets before per-file diagnostics."
        ),
    ),
    ToolParamSpec(
        name="emit_artifacts",
        type_hint="bool | null",
        required=False,
        default_value="diagnostics.default_emit_artifacts",
        description=(
            "Whether to run `lake build` for files that passed diagnostics, to emit build artifacts."
        ),
    ),
    ToolParamSpec(
        name="include_content",
        type_hint="bool | null",
        required=False,
        default_value="diagnostics.default_include_content",
        description=(
            "Whether to attach source context snippet around each diagnostic item."
        ),
    ),
    ToolParamSpec(
        name="context_lines",
        type_hint="int | null",
        required=False,
        default_value="diagnostics.default_context_lines",
        description=(
            "Number of context lines before/after diagnostic location when include_content=true."
        ),
    ),
    ToolParamSpec(
        name="timeout_seconds",
        type_hint="int | null",
        required=False,
        default_value="diagnostics.default_timeout_seconds",
        description=(
            "Command timeout (seconds) for each underlying Lean/Lake invocation."
        ),
    ),
)

_LINT_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description=(
            "Lean project root directory. If not provided, server default root is used."
        ),
    ),
    ToolParamSpec(
        name="targets",
        type_hint="list[str] | str | null",
        required=False,
        default_value="null (check all default targets)",
        description=(
            "Lean targets to check. Supports Lean dot path (A.B.C), relative .lean file path "
            "(A/B/C.lean), relative directory, or absolute path under project root."
        ),
    ),
    ToolParamSpec(
        name="enabled_checks",
        type_hint="list[str] | str | null",
        required=False,
        default_value="diagnostics.default_enabled_checks",
        description=(
            "Enabled lint checks. Current implementation supports no_sorry; unsupported checks "
            "return check-level not implemented results."
        ),
    ),
    ToolParamSpec(
        name="include_content",
        type_hint="bool | null",
        required=False,
        default_value="diagnostics.default_include_content",
        description=(
            "Whether to attach source context snippet around each diagnostic item."
        ),
    ),
    ToolParamSpec(
        name="context_lines",
        type_hint="int | null",
        required=False,
        default_value="diagnostics.default_context_lines",
        description=(
            "Number of context lines before/after diagnostic location when include_content=true."
        ),
    ),
    ToolParamSpec(
        name="timeout_seconds",
        type_hint="int | null",
        required=False,
        default_value="diagnostics.default_timeout_seconds",
        description=(
            "Command timeout (seconds) for each underlying Lean/Lake invocation."
        ),
    ),
)

_LINT_NO_SORRY_PARAMS: tuple[ToolParamSpec, ...] = tuple(
    item for item in _LINT_PARAMS if item.name != "enabled_checks"
)

_DIAGNOSTIC_ITEM_FIELDS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("severity", "str", "Diagnostic severity."),
    ToolReturnSpec("pos", "{line:int,column:int} | null", "Start position."),
    ToolReturnSpec("endPos", "{line:int,column:int} | null", "End position."),
    ToolReturnSpec("kind", "str | null", "Diagnostic kind when available."),
    ToolReturnSpec("data", "str", "Diagnostic message text."),
    ToolReturnSpec("fileName", "str | null", "Lean dot path for source file."),
    ToolReturnSpec("content", "str | null", "Attached source context snippet."),
)

_BUILD_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Overall build diagnostics success."),
    ToolReturnSpec(
        "files",
        "list[FileDiagnostics]",
        "Per-file diagnostics results.",
        children=(
            ToolReturnSpec("file", "str", "Lean dot path of file."),
            ToolReturnSpec(
                "success",
                "bool",
                "Whether this file has no error-level diagnostics.",
            ),
            ToolReturnSpec(
                "items",
                "list[DiagnosticItem]",
                "Diagnostics items for the file.",
                children=_DIAGNOSTIC_ITEM_FIELDS,
            ),
        ),
    ),
    ToolReturnSpec(
        "failed_stage",
        "null | build_deps | diagnostics | emit_artifacts",
        "Pipeline stage where execution failed, if any.",
    ),
    ToolReturnSpec(
        "stage_error_message",
        "str | null",
        "Stage-level failure message for build_deps/emit_artifacts failures.",
    ),
)

_LINT_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Overall lint success across enabled checks."),
    ToolReturnSpec(
        "checks",
        "list[CheckResult]",
        "Per-check lint results.",
        children=(
            ToolReturnSpec("check_id", "str", "Lint check identifier."),
            ToolReturnSpec("success", "bool", "Check-level pass/fail."),
            ToolReturnSpec("message", "str", "Human-readable summary for the check."),
            ToolReturnSpec(
                "sorries",
                "list[DiagnosticItem] | absent",
                "Present for `no_sorry` check.",
                children=_DIAGNOSTIC_ITEM_FIELDS,
            ),
            ToolReturnSpec(
                "<extra fields>",
                "object",
                "Check-specific fields for other lint checks.",
            ),
        ),
    ),
)

_LINT_NO_SORRY_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("check_id", "str", "Always `no_sorry`."),
    ToolReturnSpec("success", "bool", "Whether sorry diagnostics are absent."),
    ToolReturnSpec("message", "str", "Summary of no_sorry check result."),
    ToolReturnSpec(
        "sorries",
        "list[DiagnosticItem]",
        "All diagnostics classified as sorry.",
        children=_DIAGNOSTIC_ITEM_FIELDS,
    ),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.build",
        raw_name="build",
        api_path="/diagnostics/build",
        description=(
            "Run multi-file Lean build diagnostics with structured per-file output. "
            "Optionally perform dependency build and artifact emission."
        ),
        params=_BUILD_PARAMS,
        returns=_BUILD_RETURNS,
    ),
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.lint",
        raw_name="lint",
        api_path="/diagnostics/lint",
        description=(
            "Run configured lint checks and return check-level results. "
            "Lint is driven by diagnostics pipeline and check set."
        ),
        params=_LINT_PARAMS,
        returns=_LINT_RETURNS,
    ),
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.lint.no_sorry",
        raw_name="lint.no_sorry",
        api_path="/diagnostics/lint/no_sorry",
        description=(
            "Run no_sorry lint check and return all detected sorry diagnostics."
        ),
        params=_LINT_NO_SORRY_PARAMS,
        returns=_LINT_NO_SORRY_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class DiagnosticsGroupPlugin(GroupPlugin):
    group_name: str = "diagnostics"

    def create_local_service(self, config: ToolkitConfig):
        return create_diagnostics_service(config=config)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_diagnostics_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "diagnostics.build": lambda payload: handle_diagnostics_build(service, payload),
            "diagnostics.lint": lambda payload: handle_diagnostics_lint(service, payload),
            "diagnostics.lint.no_sorry": (
                lambda payload: handle_diagnostics_lint_no_sorry(service, payload)
            ),
        }

    def register_mcp_tools(
        self,
        mcp: Any,
        *,
        service: Any,
        aliases_by_canonical: Mapping[str, tuple[str, ...]],
        normalize_str_list,
        prune_none,
    ) -> None:
        build_spec = _TOOL_SPEC_MAP["diagnostics.build"]
        lint_spec = _TOOL_SPEC_MAP["diagnostics.lint"]
        lint_no_sorry_spec = _TOOL_SPEC_MAP["diagnostics.lint.no_sorry"]

        for alias in aliases_by_canonical.get("diagnostics.build", ()):
            self._register_build(
                mcp=mcp,
                alias=alias,
                spec=build_spec,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("diagnostics.lint", ()):
            self._register_lint(
                mcp=mcp,
                alias=alias,
                spec=lint_spec,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("diagnostics.lint.no_sorry", ()):
            self._register_lint_no_sorry(
                mcp=mcp,
                alias=alias,
                spec=lint_no_sorry_spec,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )

    @staticmethod
    def _register_build(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        def _diagnostics_build(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            targets: Annotated[
                list[str] | str | None,
                Field(description=_param_desc(spec, "targets")),
            ] = None,
            build_deps: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "build_deps")),
            ] = None,
            emit_artifacts: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "emit_artifacts")),
            ] = None,
            include_content: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "include_content")),
            ] = None,
            context_lines: Annotated[
                int | None,
                Field(description=_param_desc(spec, "context_lines")),
            ] = None,
            timeout_seconds: Annotated[
                int | None,
                Field(description=_param_desc(spec, "timeout_seconds")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "build_deps": build_deps,
                "emit_artifacts": emit_artifacts,
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_build(service, prune_none(payload))

    @staticmethod
    def _register_lint(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        def _diagnostics_lint(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            targets: Annotated[
                list[str] | str | None,
                Field(description=_param_desc(spec, "targets")),
            ] = None,
            enabled_checks: Annotated[
                list[str] | str | None,
                Field(description=_param_desc(spec, "enabled_checks")),
            ] = None,
            include_content: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "include_content")),
            ] = None,
            context_lines: Annotated[
                int | None,
                Field(description=_param_desc(spec, "context_lines")),
            ] = None,
            timeout_seconds: Annotated[
                int | None,
                Field(description=_param_desc(spec, "timeout_seconds")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "enabled_checks": normalize_str_list(enabled_checks),
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_lint(service, prune_none(payload))

    @staticmethod
    def _register_lint_no_sorry(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        def _diagnostics_lint_no_sorry(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            targets: Annotated[
                list[str] | str | None,
                Field(description=_param_desc(spec, "targets")),
            ] = None,
            include_content: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "include_content")),
            ] = None,
            context_lines: Annotated[
                int | None,
                Field(description=_param_desc(spec, "context_lines")),
            ] = None,
            timeout_seconds: Annotated[
                int | None,
                Field(description=_param_desc(spec, "timeout_seconds")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_lint_no_sorry(service, prune_none(payload))


__all__ = ["DiagnosticsGroupPlugin"]
