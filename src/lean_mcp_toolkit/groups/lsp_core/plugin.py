"""lsp_core group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_lsp_code_actions,
    handle_lsp_file_outline,
    handle_lsp_goal,
    handle_lsp_hover,
    handle_lsp_run_snippet,
    handle_lsp_term_goal,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
    run_sync_mcp_service_handler,
)
from .factory import create_lsp_core_client, create_lsp_core_service


_COMMON_FILE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description="Lean project root directory. If not provided, server default root is used.",
    ),
    ToolParamSpec(
        name="file_path",
        type_hint="str",
        required=True,
        description=(
            "Lean file path. Supports Lean dot path, relative .lean path, "
            "or absolute .lean path under project root."
        ),
    ),
)

_RESPONSE_FORMAT_PARAM = ToolParamSpec(
    name="response_format",
    type_hint='"structured" | "markdown" | null',
    required=False,
    default_value="lsp_core.default_response_format",
    description="Output format for this request.",
)

_FILE_OUTLINE_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(
        name="max_declarations",
        type_hint="int | null",
        required=False,
        default_value="lsp_core.default_max_declarations",
        description="Maximum declarations to return.",
    ),
    _RESPONSE_FORMAT_PARAM,
)

_GOAL_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    ToolParamSpec(
        name="column",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Column number (1-based). Omit to get goals_before/goals_after.",
    ),
    _RESPONSE_FORMAT_PARAM,
)

_TERM_GOAL_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    ToolParamSpec(
        name="column",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Column number (1-based). Omit to use line end.",
    ),
    _RESPONSE_FORMAT_PARAM,
)

_HOVER_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    ToolParamSpec(name="column", type_hint="int", required=True, description="Column number (1-based)."),
    ToolParamSpec(
        name="include_diagnostics",
        type_hint="bool | null",
        required=False,
        default_value="lsp_core.hover_include_diagnostics_default",
        description="Whether to include diagnostics covering this position.",
    ),
    _RESPONSE_FORMAT_PARAM,
)

_CODE_ACTION_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    _RESPONSE_FORMAT_PARAM,
)

_RUN_SNIPPET_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description="Lean project root directory. If not provided, server default root is used.",
    ),
    ToolParamSpec(
        name="code",
        type_hint="str",
        required=True,
        description="Self-contained Lean code snippet with required imports.",
    ),
    ToolParamSpec(
        name="timeout_seconds",
        type_hint="int | null",
        required=False,
        default_value="lsp_core.run_snippet_default_timeout_seconds",
        description="Diagnostics wait timeout in seconds. Values above lsp_core.run_snippet_max_timeout_seconds are clamped.",
    ),
)

_MARKDOWN_RETURN: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("markdown", "str", "Rendered markdown output when response_format=markdown."),
)

_FILE_OUTLINE_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether file outline succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("imports", "list[str]", "Imported modules from file header."),
    ToolReturnSpec(
        "declarations",
        "list[OutlineEntry]",
        "Document symbol tree.",
        children=(
            ToolReturnSpec("name", "str", "Declaration/symbol name."),
            ToolReturnSpec("kind", "str", "Declaration/symbol kind."),
            ToolReturnSpec("start_line", "int", "1-based start line."),
            ToolReturnSpec("end_line", "int", "1-based end line."),
            ToolReturnSpec("type_signature", "str | null", "Type signature/detail."),
            ToolReturnSpec("children", "list[OutlineEntry]", "Nested child symbols."),
        ),
    ),
    ToolReturnSpec("total_declarations", "int | null", "Original declaration count when truncated."),
    *_MARKDOWN_RETURN,
)

_GOAL_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether goal query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("line_context", "str | null", "Source line content at requested line."),
    ToolReturnSpec("goals", "list[str] | null", "Goals at provided position (column mode)."),
    ToolReturnSpec("goals_before", "list[str] | null", "Goals at line start (column omitted)."),
    ToolReturnSpec("goals_after", "list[str] | null", "Goals at line end (column omitted)."),
    *_MARKDOWN_RETURN,
)

_TERM_GOAL_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether term goal query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("line_context", "str | null", "Source line content at requested line."),
    ToolReturnSpec("expected_type", "str | null", "Expected type at position."),
    *_MARKDOWN_RETURN,
)

_HOVER_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether hover query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("symbol", "str | null", "Symbol text at requested position."),
    ToolReturnSpec("info", "str | null", "Hover information text."),
    ToolReturnSpec(
        "diagnostics",
        "list[DiagnosticMessage]",
        "Diagnostics covering requested position.",
        children=(
            ToolReturnSpec("severity", "str", "Diagnostic severity."),
            ToolReturnSpec("message", "str", "Diagnostic message."),
            ToolReturnSpec("line", "int", "1-based line."),
            ToolReturnSpec("column", "int", "1-based column."),
        ),
    ),
    *_MARKDOWN_RETURN,
)

_CODE_ACTION_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether code action query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec(
        "actions",
        "list[CodeAction]",
        "Resolved code actions for line diagnostics.",
        children=(
            ToolReturnSpec("title", "str", "Action title."),
            ToolReturnSpec("is_preferred", "bool", "Whether action is preferred."),
            ToolReturnSpec(
                "edits",
                "list[CodeActionEdit]",
                "Resolved text edits.",
                children=(
                    ToolReturnSpec("new_text", "str", "Replacement text."),
                    ToolReturnSpec("start_line", "int", "1-based start line."),
                    ToolReturnSpec("start_column", "int", "1-based start column."),
                    ToolReturnSpec("end_line", "int", "1-based end line."),
                    ToolReturnSpec("end_column", "int", "1-based end column."),
                ),
            ),
        ),
    ),
    *_MARKDOWN_RETURN,
)

_RUN_SNIPPET_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether snippet has no error diagnostics."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec(
        "diagnostics",
        "list[DiagnosticMessage]",
        "Snippet diagnostics.",
        children=(
            ToolReturnSpec("severity", "str", "Diagnostic severity."),
            ToolReturnSpec("message", "str", "Diagnostic message."),
            ToolReturnSpec("line", "int", "1-based line."),
            ToolReturnSpec("column", "int", "1-based column."),
        ),
    ),
    ToolReturnSpec("error_count", "int", "Error diagnostics count."),
    ToolReturnSpec("warning_count", "int", "Warning diagnostics count."),
    ToolReturnSpec("info_count", "int", "Info/hint diagnostics count."),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.file_outline",
        raw_name="file_outline",
        api_path="/lsp/file_outline",
        description="Get imports and declaration outline for a Lean file.",
        params=_FILE_OUTLINE_PARAMS,
        returns=_FILE_OUTLINE_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.goal",
        raw_name="goal",
        api_path="/lsp/goal",
        description="Get proof goals at a position, or before/after line when column omitted.",
        params=_GOAL_PARAMS,
        returns=_GOAL_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.term_goal",
        raw_name="term_goal",
        api_path="/lsp/term_goal",
        description="Get expected type at a position.",
        params=_TERM_GOAL_PARAMS,
        returns=_TERM_GOAL_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.hover",
        raw_name="hover",
        api_path="/lsp/hover",
        description="Get hover info and optional diagnostics for a symbol position.",
        params=_HOVER_PARAMS,
        returns=_HOVER_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.code_actions",
        raw_name="code_actions",
        api_path="/lsp/code_actions",
        description="Get resolved code actions for diagnostics on a line.",
        params=_CODE_ACTION_PARAMS,
        returns=_CODE_ACTION_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.run_snippet",
        raw_name="run_snippet",
        api_path="/lsp/run_snippet",
        description="Run a standalone Lean snippet and return diagnostics.",
        params=_RUN_SNIPPET_PARAMS,
        returns=_RUN_SNIPPET_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class LspCoreGroupPlugin(GroupPlugin):
    group_name: str = "lsp_core"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LSP_CLIENT_MANAGER,)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_lsp_core_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_lsp_core_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "lsp.file_outline": lambda payload: handle_lsp_file_outline(service, payload),
            "lsp.goal": lambda payload: handle_lsp_goal(service, payload),
            "lsp.term_goal": lambda payload: handle_lsp_term_goal(service, payload),
            "lsp.hover": lambda payload: handle_lsp_hover(service, payload),
            "lsp.code_actions": lambda payload: handle_lsp_code_actions(service, payload),
            "lsp.run_snippet": lambda payload: handle_lsp_run_snippet(service, payload),
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
        _ = normalize_str_list
        for canonical in _TOOL_SPEC_MAP:
            spec = _TOOL_SPEC_MAP[canonical]
            for alias in aliases_by_canonical.get(canonical, ()):  # pragma: no branch
                self._register_one(
                    mcp=mcp,
                    alias=alias,
                    spec=spec,
                    service=service,
                    prune_none=prune_none,
                )

    @staticmethod
    def _register_one(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        if spec.canonical_name == "lsp.file_outline":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_file_outline(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                max_declarations: Annotated[int | None, Field(description=_param_desc(spec, "max_declarations"))] = None,
                response_format: Annotated[str | None, Field(description=_param_desc(spec, "response_format"))] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "max_declarations": max_declarations,
                    "response_format": response_format,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_file_outline,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.goal":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_goal(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
                column: Annotated[int | None, Field(description=_param_desc(spec, "column"), ge=1)] = None,
                response_format: Annotated[str | None, Field(description=_param_desc(spec, "response_format"))] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "line": line,
                    "column": column,
                    "response_format": response_format,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_goal,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.term_goal":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_term_goal(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
                column: Annotated[int | None, Field(description=_param_desc(spec, "column"), ge=1)] = None,
                response_format: Annotated[str | None, Field(description=_param_desc(spec, "response_format"))] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "line": line,
                    "column": column,
                    "response_format": response_format,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_term_goal,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.hover":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_hover(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
                column: Annotated[int, Field(description=_param_desc(spec, "column"), ge=1)] = 1,
                include_diagnostics: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_diagnostics")),
                ] = None,
                response_format: Annotated[str | None, Field(description=_param_desc(spec, "response_format"))] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "line": line,
                    "column": column,
                    "include_diagnostics": include_diagnostics,
                    "response_format": response_format,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_hover,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.run_snippet":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_run_snippet(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                code: Annotated[str, Field(description=_param_desc(spec, "code"))] = "",
                timeout_seconds: Annotated[int | None, Field(description=_param_desc(spec, "timeout_seconds"), ge=1)] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "code": code,
                    "timeout_seconds": timeout_seconds,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_run_snippet,
                    service,
                    prune_none(payload),
                )

            return

        @mcp.tool(name=alias, description=spec.render_mcp_description())
        async def _lsp_code_actions(
            project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
            file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
            line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
            response_format: Annotated[str | None, Field(description=_param_desc(spec, "response_format"))] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "file_path": file_path,
                "line": line,
                "response_format": response_format,
            }
            return await run_sync_mcp_service_handler(
                handle_lsp_code_actions,
                service,
                prune_none(payload),
            )


__all__ = ["LspCoreGroupPlugin"]
