"""lsp_assist group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_lsp_completions,
    handle_lsp_declaration_file,
    handle_lsp_multi_attempt,
    handle_lsp_theorem_soundness,
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
from .factory import create_lsp_assist_client, create_lsp_assist_service

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

_COMPLETIONS_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    ToolParamSpec(name="column", type_hint="int", required=True, description="Column number (1-based)."),
    ToolParamSpec(
        name="max_completions",
        type_hint="int | null",
        required=False,
        default_value="lsp_assist.default_max_completions",
        description="Maximum completion items to return.",
    ),
)

_DECLARATION_FILE_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(
        name="symbol",
        type_hint="str",
        required=True,
        description="Symbol (case sensitive, must appear in source file).",
    ),
    ToolParamSpec(
        name="line",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Optional 1-based line for precise symbol occurrence.",
    ),
    ToolParamSpec(
        name="column",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Optional 1-based column for precise symbol occurrence.",
    ),
    ToolParamSpec(
        name="include_file_content",
        type_hint="bool | null",
        required=False,
        default_value="lsp_assist.declaration_file_include_content_default",
        description="Whether to include target declaration file content.",
    ),
)

_MULTI_ATTEMPT_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(name="line", type_hint="int", required=True, description="Line number (1-based)."),
    ToolParamSpec(
        name="snippets",
        type_hint="list[str]",
        required=True,
        description="Tactic/code snippets to try.",
    ),
    ToolParamSpec(
        name="max_attempts",
        type_hint="int | null",
        required=False,
        default_value="lsp_assist.multi_attempt_default_max_attempts",
        description="Optional per-call cap before hard limit is applied.",
    ),
)

_THEOREM_SOUNDNESS_PARAMS: tuple[ToolParamSpec, ...] = (
    *_COMMON_FILE_PARAMS,
    ToolParamSpec(
        name="theorem_name",
        type_hint="str",
        required=True,
        description="Theorem full name (recommended) or accessible name in imported module.",
    ),
    ToolParamSpec(
        name="scan_source",
        type_hint="bool | null",
        required=False,
        default_value="lsp_assist.theorem_soundness_scan_source_default",
        description="Whether to scan source file for suspicious patterns.",
    ),
)

_DIAGNOSTIC_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("severity", "str", "Diagnostic severity."),
    ToolReturnSpec("message", "str", "Diagnostic message."),
    ToolReturnSpec("line", "int", "1-based line."),
    ToolReturnSpec("column", "int", "1-based column."),
)

_COMPLETIONS_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether completion query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec(
        "items",
        "list[CompletionItem]",
        "Completion items.",
        children=(
            ToolReturnSpec("label", "str", "Completion label."),
            ToolReturnSpec("kind", "str | null", "Completion item kind."),
            ToolReturnSpec("detail", "str | null", "Additional detail."),
        ),
    ),
    ToolReturnSpec("count", "int", "Number of completion items."),
)

_DECLARATION_FILE_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether declaration lookup succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec(
        "source_pos",
        "Position | null",
        "Resolved source position.",
        children=(
            ToolReturnSpec("line", "int", "1-based line."),
            ToolReturnSpec("column", "int", "1-based column."),
        ),
    ),
    ToolReturnSpec("target_file_path", "str | null", "Absolute target file path."),
    ToolReturnSpec("target_file_uri", "str | null", "Target file URI from LSP."),
    ToolReturnSpec(
        "target_range",
        "Range | null",
        "Target declaration range.",
        children=(
            ToolReturnSpec(
                "start",
                "Position",
                "Range start.",
                children=(
                    ToolReturnSpec("line", "int", "1-based line."),
                    ToolReturnSpec("column", "int", "1-based column."),
                ),
            ),
            ToolReturnSpec(
                "end",
                "Position",
                "Range end.",
                children=(
                    ToolReturnSpec("line", "int", "1-based line."),
                    ToolReturnSpec("column", "int", "1-based column."),
                ),
            ),
        ),
    ),
    ToolReturnSpec("target_selection_range", "Range | null", "Selection range for declaration symbol."),
    ToolReturnSpec("content", "str | null", "Optional target file content."),
)

_MULTI_ATTEMPT_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether multi-attempt execution succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec(
        "items",
        "list[AttemptResult]",
        "Per-snippet attempt results.",
        children=(
            ToolReturnSpec("snippet", "str", "Snippet content."),
            ToolReturnSpec("goals", "list[str]", "Goals after snippet application."),
            ToolReturnSpec("diagnostics", "list[DiagnosticMessage]", "Diagnostics for this attempt.", children=_DIAGNOSTIC_RETURNS),
            ToolReturnSpec("attempt_success", "bool", "Whether this attempt has no error diagnostics."),
            ToolReturnSpec("goal_count", "int", "Number of goals."),
        ),
    ),
    ToolReturnSpec("count", "int", "Number of attempts executed."),
    ToolReturnSpec("any_success", "bool", "Whether any attempt succeeded."),
)

_THEOREM_SOUNDNESS_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether theorem soundness check succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("axioms", "list[str]", "Axioms reported by `#print axioms`."),
    ToolReturnSpec(
        "warnings",
        "list[SourceWarning]",
        "Suspicious source patterns from optional source scan.",
        children=(
            ToolReturnSpec("line", "int", "1-based line (0 means unavailable)."),
            ToolReturnSpec("pattern", "str", "Matched pattern text."),
        ),
    ),
    ToolReturnSpec("axiom_count", "int", "Axiom count."),
    ToolReturnSpec("warning_count", "int", "Warning count."),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="lsp_assist",
        canonical_name="lsp.completions",
        raw_name="completions",
        api_path="/lsp/completions",
        description="Get IDE autocompletions at a given file position.",
        params=_COMPLETIONS_PARAMS,
        returns=_COMPLETIONS_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_assist",
        canonical_name="lsp.declaration_file",
        raw_name="declaration_file",
        api_path="/lsp/declaration_file",
        description="Resolve declaration location for a symbol from file context.",
        params=_DECLARATION_FILE_PARAMS,
        returns=_DECLARATION_FILE_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_assist",
        canonical_name="lsp.multi_attempt",
        raw_name="multi_attempt",
        api_path="/lsp/multi_attempt",
        description="Try multiple snippets around a tactic line and collect goals/diagnostics.",
        params=_MULTI_ATTEMPT_PARAMS,
        returns=_MULTI_ATTEMPT_RETURNS,
    ),
    GroupToolSpec(
        group_name="lsp_assist",
        canonical_name="lsp.theorem_soundness",
        raw_name="theorem_soundness",
        api_path="/lsp/theorem_soundness",
        description="Check theorem axioms and optionally scan source for suspicious patterns.",
        params=_THEOREM_SOUNDNESS_PARAMS,
        returns=_THEOREM_SOUNDNESS_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class LspAssistGroupPlugin(GroupPlugin):
    group_name: str = "lsp_assist"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LSP_CLIENT_MANAGER,)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_lsp_assist_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_lsp_assist_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "lsp.completions": lambda payload: handle_lsp_completions(service, payload),
            "lsp.declaration_file": lambda payload: handle_lsp_declaration_file(service, payload),
            "lsp.multi_attempt": lambda payload: handle_lsp_multi_attempt(service, payload),
            "lsp.theorem_soundness": lambda payload: handle_lsp_theorem_soundness(service, payload),
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
            for alias in aliases_by_canonical.get(canonical, ()):
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
        if spec.canonical_name == "lsp.completions":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_completions(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
                column: Annotated[int, Field(description=_param_desc(spec, "column"), ge=1)] = 1,
                max_completions: Annotated[int | None, Field(description=_param_desc(spec, "max_completions"), ge=1)] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "line": line,
                    "column": column,
                    "max_completions": max_completions,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_completions,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.declaration_file":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_declaration_file(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                symbol: Annotated[str, Field(description=_param_desc(spec, "symbol"))] = "",
                line: Annotated[int | None, Field(description=_param_desc(spec, "line"), ge=1)] = None,
                column: Annotated[int | None, Field(description=_param_desc(spec, "column"), ge=1)] = None,
                include_file_content: Annotated[bool | None, Field(description=_param_desc(spec, "include_file_content"))] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "symbol": symbol,
                    "line": line,
                    "column": column,
                    "include_file_content": include_file_content,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_declaration_file,
                    service,
                    prune_none(payload),
                )

            return

        if spec.canonical_name == "lsp.multi_attempt":

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _lsp_multi_attempt(
                project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
                file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"), ge=1)] = 1,
                snippets: Annotated[list[str] | None, Field(description=_param_desc(spec, "snippets"))] = None,
                max_attempts: Annotated[int | None, Field(description=_param_desc(spec, "max_attempts"), ge=1)] = None,
            ) -> JsonDict:
                payload = {
                    "project_root": project_root,
                    "file_path": file_path,
                    "line": line,
                    "snippets": snippets or [],
                    "max_attempts": max_attempts,
                }
                return await run_sync_mcp_service_handler(
                    handle_lsp_multi_attempt,
                    service,
                    prune_none(payload),
                )

            return

        @mcp.tool(name=alias, description=spec.render_mcp_description())
        async def _lsp_theorem_soundness(
            project_root: Annotated[str | None, Field(description=_param_desc(spec, "project_root"))] = None,
            file_path: Annotated[str, Field(description=_param_desc(spec, "file_path"))] = "",
            theorem_name: Annotated[str, Field(description=_param_desc(spec, "theorem_name"))] = "",
            scan_source: Annotated[bool | None, Field(description=_param_desc(spec, "scan_source"))] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "file_path": file_path,
                "theorem_name": theorem_name,
                "scan_source": scan_source,
            }
            return await run_sync_mcp_service_handler(
                handle_lsp_theorem_soundness,
                service,
                prune_none(payload),
            )


__all__ = ["LspAssistGroupPlugin"]
