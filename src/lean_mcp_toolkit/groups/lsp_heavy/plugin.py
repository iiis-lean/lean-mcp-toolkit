"""lsp_heavy group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_lsp_proof_profile,
    handle_lsp_widget_source,
    handle_lsp_widgets,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...contracts.lsp_heavy import (
    LspProofProfileResponse,
    LspWidgetSourceResponse,
    LspWidgetsResponse,
)
from ...transport.http import HttpConfig
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
    run_sync_mcp_service_handler,
    with_output_schemas,
)
from .factory import create_lsp_heavy_client, create_lsp_heavy_service

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

_BASE_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="lsp_heavy",
        canonical_name="lsp.widgets",
        raw_name="widgets",
        api_path="/lsp/widgets",
        description="Get panel widgets at a Lean source position.",
        params=(
            *_COMMON_FILE_PARAMS,
            ToolParamSpec("line", "int", "Line number (1-based).", required=True),
            ToolParamSpec("column", "int", "Column number (1-based).", required=True),
        ),
        returns=(
            ToolReturnSpec("success", "bool", "Whether widget lookup succeeded."),
            ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
            ToolReturnSpec("widgets", "list[WidgetInstance]", "Widget instances at the position."),
            ToolReturnSpec("count", "int", "Number of widget instances."),
        ),
    ),
    GroupToolSpec(
        group_name="lsp_heavy",
        canonical_name="lsp.widget_source",
        raw_name="widget_source",
        api_path="/lsp/widget_source",
        description="Get JavaScript source payload for a widget hash.",
        params=(
            *_COMMON_FILE_PARAMS,
            ToolParamSpec(
                "javascript_hash",
                "str",
                "Widget JavaScript hash returned by `lsp.widgets`.",
                required=True,
            ),
        ),
        returns=(
            ToolReturnSpec("success", "bool", "Whether widget source lookup succeeded."),
            ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
            ToolReturnSpec("javascript_hash", "str", "Requested JavaScript hash."),
            ToolReturnSpec(
                "source_text",
                "str | null",
                "Extracted widget source text when available.",
            ),
            ToolReturnSpec("raw_source", "JsonDict | null", "Raw widget source payload."),
        ),
    ),
    GroupToolSpec(
        group_name="lsp_heavy",
        canonical_name="lsp.proof_profile",
        raw_name="proof_profile",
        api_path="/lsp/proof_profile",
        description="Profile a theorem proof using `lean --profile`.",
        params=(
            *_COMMON_FILE_PARAMS,
            ToolParamSpec("line", "int", "Declaration line (1-based).", required=True),
            ToolParamSpec(
                "top_n",
                "int | null",
                description="Number of slow proof lines to keep.",
                required=False,
                default_value="lsp_heavy.proof_profile_default_top_n",
            ),
            ToolParamSpec(
                "timeout_seconds",
                "int | null",
                description="Profiling timeout in seconds.",
                required=False,
                default_value="lsp_heavy.proof_profile_default_timeout_seconds",
            ),
        ),
        returns=(
            ToolReturnSpec("success", "bool", "Whether profiling succeeded."),
            ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
            ToolReturnSpec("theorem_name", "str | null", "Profiled declaration name."),
            ToolReturnSpec("total_ms", "float | null", "Total profile time in milliseconds."),
            ToolReturnSpec("lines", "list[ProfileLine]", "Top slow proof lines."),
            ToolReturnSpec("count", "int", "Number of profile lines."),
            ToolReturnSpec("categories", "list[ProfileCategory]", "Profile categories."),
            ToolReturnSpec("category_count", "int", "Number of profile categories."),
        ),
    ),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = with_output_schemas(
    _BASE_TOOL_SPECS,
    {
        "lsp.widgets": LspWidgetsResponse,
        "lsp.widget_source": LspWidgetSourceResponse,
        "lsp.proof_profile": LspProofProfileResponse,
    },
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class LspHeavyGroupPlugin(GroupPlugin):
    group_name: str = "lsp_heavy"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LSP_CLIENT_MANAGER,)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_lsp_heavy_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_lsp_heavy_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "lsp.widgets": lambda payload: handle_lsp_widgets(service, payload),
            "lsp.widget_source": lambda payload: handle_lsp_widget_source(service, payload),
            "lsp.proof_profile": lambda payload: handle_lsp_proof_profile(service, payload),
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
        spec = _TOOL_SPEC_MAP["lsp.widgets"]
        for alias in aliases_by_canonical.get("lsp.widgets", ()):
            @mcp.tool(name=alias, description=spec.render_mcp_description(), structured_output=True)
            async def _lsp_widgets(
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                file_path: Annotated[
                    str,
                    Field(description=_param_desc(spec, "file_path")),
                ] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"))] = 1,
                column: Annotated[int, Field(description=_param_desc(spec, "column"))] = 1,
            ) -> LspWidgetsResponse:
                return await run_sync_mcp_service_handler(
                    handle_lsp_widgets,
                    service,
                    prune_none(
                        {
                            "project_root": project_root,
                            "file_path": file_path,
                            "line": line,
                            "column": column,
                        }
                    ),
                )

        spec = _TOOL_SPEC_MAP["lsp.widget_source"]
        for alias in aliases_by_canonical.get("lsp.widget_source", ()):
            @mcp.tool(name=alias, description=spec.render_mcp_description(), structured_output=True)
            async def _lsp_widget_source(
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                file_path: Annotated[
                    str,
                    Field(description=_param_desc(spec, "file_path")),
                ] = "",
                javascript_hash: Annotated[
                    str,
                    Field(description=_param_desc(spec, "javascript_hash")),
                ] = "",
            ) -> LspWidgetSourceResponse:
                return await run_sync_mcp_service_handler(
                    handle_lsp_widget_source,
                    service,
                    prune_none(
                        {
                            "project_root": project_root,
                            "file_path": file_path,
                            "javascript_hash": javascript_hash,
                        }
                    ),
                )

        spec = _TOOL_SPEC_MAP["lsp.proof_profile"]
        for alias in aliases_by_canonical.get("lsp.proof_profile", ()):
            @mcp.tool(name=alias, description=spec.render_mcp_description(), structured_output=True)
            async def _lsp_proof_profile(
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                file_path: Annotated[
                    str,
                    Field(description=_param_desc(spec, "file_path")),
                ] = "",
                line: Annotated[int, Field(description=_param_desc(spec, "line"))] = 1,
                top_n: Annotated[int | None, Field(description=_param_desc(spec, "top_n"))] = None,
                timeout_seconds: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "timeout_seconds")),
                ] = None,
            ) -> LspProofProfileResponse:
                return await run_sync_mcp_service_handler(
                    handle_lsp_proof_profile,
                    service,
                    prune_none(
                        {
                            "project_root": project_root,
                            "file_path": file_path,
                            "line": line,
                            "top_n": top_n,
                            "timeout_seconds": timeout_seconds,
                        }
                    ),
                )


__all__ = ["LspHeavyGroupPlugin"]
