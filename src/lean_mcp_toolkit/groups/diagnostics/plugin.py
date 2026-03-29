"""Diagnostics group plugin."""

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
    handle_diagnostics_file,
    handle_diagnostics_lint,
    handle_diagnostics_lint_axiom_audit,
    handle_diagnostics_lint_no_sorry,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
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
    run_sync_mcp_service_handler,
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
            "Whether to run `lake build <module>:deps` before per-file diagnostics, "
            "so only target dependencies are prebuilt."
        ),
    ),
    ToolParamSpec(
        name="emit_artifacts",
        type_hint="bool | null",
        required=False,
        default_value="diagnostics.default_emit_artifacts",
        description=(
            "Whether to run `lake build <module>:leanArts` for files that passed diagnostics, "
            "to emit target Lean artifacts."
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

_FILE_PARAMS: tuple[ToolParamSpec, ...] = (
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
        name="file_path",
        type_hint="str",
        required=True,
        description=(
            "Single Lean file target to check. Supports Lean dot path (A.B.C), "
            "relative .lean path (A/B/C.lean), or absolute path under project root."
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
            "Command timeout (seconds) for underlying diagnostics collection."
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
            "Enabled lint checks. Implemented checks: no_sorry and axiom_audit. "
            "Unsupported checks return check-level not implemented results."
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

_FILE_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether file has no error-level diagnostics."),
    ToolReturnSpec("error_message", "str | null", "Execution failure detail, if any."),
    ToolReturnSpec("file", "str", "Lean dot path for checked file."),
    ToolReturnSpec(
        "items",
        "list[DiagnosticItem]",
        "Diagnostics items for the file.",
        children=_DIAGNOSTIC_ITEM_FIELDS,
    ),
    ToolReturnSpec("total_items", "int", "Total diagnostics items count."),
    ToolReturnSpec("error_count", "int", "Count of error diagnostics."),
    ToolReturnSpec("warning_count", "int", "Count of warning diagnostics."),
    ToolReturnSpec("info_count", "int", "Count of information/hint diagnostics."),
    ToolReturnSpec("sorry_count", "int", "Count of diagnostics identified as sorry."),
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
                "declared_axioms",
                "list[{fileName:str|null,declaration:str|null,kind:str|null,pos:{line:int,column:int}|null,endPos:{line:int,column:int}|null,content:str|null}] | absent",
                "Present for `axiom_audit` check.",
            ),
            ToolReturnSpec(
                "usage_issues",
                "list[{fileName:str|null,declaration:str|null,risky_axioms:list[str]}] | absent",
                "Present for `axiom_audit` check.",
            ),
            ToolReturnSpec(
                "unresolved",
                "list[{fileName:str|null,declaration:str|null,reason:str}] | absent",
                "Present for `axiom_audit` check.",
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

_LINT_AXIOM_AUDIT_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("check_id", "str", "Always `axiom_audit`."),
    ToolReturnSpec("success", "bool", "Whether declared axioms/risky usage are absent."),
    ToolReturnSpec("message", "str", "Summary of axiom_audit check result."),
    ToolReturnSpec(
        "declared_axioms",
        "list[{fileName:str|null,declaration:str|null,kind:str|null,pos:{line:int,column:int}|null,endPos:{line:int,column:int}|null,content:str|null}]",
        "Declared axioms/constant declarations found in targets.",
    ),
    ToolReturnSpec(
        "usage_issues",
        "list[{fileName:str|null,declaration:str|null,risky_axioms:list[str]}]",
        "Declarations depending on risky axioms.",
    ),
    ToolReturnSpec(
        "unresolved",
        "list[{fileName:str|null,declaration:str|null,reason:str}]",
        "Declarations/files that could not be audited.",
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
        canonical_name="diagnostics.file",
        raw_name="file",
        api_path="/diagnostics/file",
        description=(
            "Run Lean diagnostics for a single file and return structured item-level output."
        ),
        params=_FILE_PARAMS,
        returns=_FILE_RETURNS,
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
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.lint.axiom_audit",
        raw_name="lint.axiom_audit",
        api_path="/diagnostics/lint/axiom_audit",
        description=(
            "Run axiom_audit lint check and return declared-axiom and risky-usage findings."
        ),
        params=_LINT_NO_SORRY_PARAMS,
        returns=_LINT_AXIOM_AUDIT_RETURNS,
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

    def backend_dependencies(self) -> tuple[str, ...]:
        return (
            BackendKey.LEAN_COMMAND_RUNTIME,
            BackendKey.LEAN_TARGET_RESOLVER,
            BackendKey.DECLARATIONS_BACKENDS,
            BackendKey.LSP_CLIENT_MANAGER,
        )

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_diagnostics_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_diagnostics_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "diagnostics.build": lambda payload: handle_diagnostics_build(service, payload),
            "diagnostics.file": lambda payload: handle_diagnostics_file(service, payload),
            "diagnostics.lint": lambda payload: handle_diagnostics_lint(service, payload),
            "diagnostics.lint.no_sorry": (
                lambda payload: handle_diagnostics_lint_no_sorry(service, payload)
            ),
            "diagnostics.lint.axiom_audit": (
                lambda payload: handle_diagnostics_lint_axiom_audit(service, payload)
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
        file_spec = _TOOL_SPEC_MAP["diagnostics.file"]
        lint_spec = _TOOL_SPEC_MAP["diagnostics.lint"]
        lint_no_sorry_spec = _TOOL_SPEC_MAP["diagnostics.lint.no_sorry"]
        lint_axiom_audit_spec = _TOOL_SPEC_MAP["diagnostics.lint.axiom_audit"]

        for alias in aliases_by_canonical.get("diagnostics.build", ()):
            self._register_build(
                mcp=mcp,
                alias=alias,
                spec=build_spec,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("diagnostics.file", ()):
            self._register_file(
                mcp=mcp,
                alias=alias,
                spec=file_spec,
                service=service,
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
        for alias in aliases_by_canonical.get("diagnostics.lint.axiom_audit", ()):
            self._register_lint_axiom_audit(
                mcp=mcp,
                alias=alias,
                spec=lint_axiom_audit_spec,
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
        async def _diagnostics_build(
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
            return await run_sync_mcp_service_handler(
                handle_diagnostics_build,
                service,
                prune_none(payload),
            )

    @staticmethod
    def _register_file(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        async def _diagnostics_file(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            file_path: Annotated[
                str,
                Field(description=_param_desc(spec, "file_path")),
            ] = "",
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
                "file_path": file_path,
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return await run_sync_mcp_service_handler(
                handle_diagnostics_file,
                service,
                prune_none(payload),
            )

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
        async def _diagnostics_lint(
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
            return await run_sync_mcp_service_handler(
                handle_diagnostics_lint,
                service,
                prune_none(payload),
            )

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
        async def _diagnostics_lint_no_sorry(
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
            return await run_sync_mcp_service_handler(
                handle_diagnostics_lint_no_sorry,
                service,
                prune_none(payload),
            )

    @staticmethod
    def _register_lint_axiom_audit(
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
        async def _diagnostics_lint_axiom_audit(
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
            return await run_sync_mcp_service_handler(
                handle_diagnostics_lint_axiom_audit,
                service,
                prune_none(payload),
            )


__all__ = ["DiagnosticsGroupPlugin"]
