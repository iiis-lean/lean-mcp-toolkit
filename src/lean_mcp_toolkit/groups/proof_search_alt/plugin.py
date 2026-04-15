"""proof_search_alt group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_proof_search_alt_hammer_premise,
    handle_proof_search_alt_state_search,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseResponse,
    ProofSearchAltStateSearchResponse,
)
from ...transport.http import HttpConfig
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
    run_sync_mcp_service_handler,
)
from .factory import create_proof_search_alt_client, create_proof_search_alt_service

_COMMON_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("project_root", "str | null", "Lean project root directory.", required=False, default_value="server default project root"),
    ToolParamSpec("file_path", "str", "Lean file path.", required=True),
    ToolParamSpec("line", "int", "Line number (1-based).", required=True),
    ToolParamSpec("column", "int", "Column number (1-based).", required=True),
    ToolParamSpec("num_results", "int | null", "Maximum results to return.", required=False, default_value="group default"),
)

_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether provider query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("provider", "str", "Provider name."),
    ToolReturnSpec("goal", "str | null", "Goal text used for provider request."),
    ToolReturnSpec("backend_mode", "str", "Backend mode."),
    ToolReturnSpec("items", "list[...]", "Result items."),
    ToolReturnSpec("count", "int", "Number of items."),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec("proof_search_alt", "proof_search_alt.state_search", "state_search", "/proof_search_alt/state_search", "Search lemmas by current goal state.", _COMMON_PARAMS, _RETURNS),
    GroupToolSpec("proof_search_alt", "proof_search_alt.hammer_premise", "hammer_premise", "/proof_search_alt/hammer_premise", "Retrieve premise suggestions for current goal.", _COMMON_PARAMS, _RETURNS),
)

_TOOL_SPEC_MAP = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class ProofSearchAltGroupPlugin(GroupPlugin):
    group_name: str = "proof_search_alt"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LSP_CLIENT_MANAGER, BackendKey.PROOF_SEARCH_ALT_MANAGER)

    def create_local_service(self, config: ToolkitConfig, *, backends: BackendContext | None = None):
        return create_proof_search_alt_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_proof_search_alt_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "proof_search_alt.state_search": lambda payload: handle_proof_search_alt_state_search(service, payload),
            "proof_search_alt.hammer_premise": lambda payload: handle_proof_search_alt_hammer_premise(service, payload),
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
        handler_map = {
            "proof_search_alt.state_search": handle_proof_search_alt_state_search,
            "proof_search_alt.hammer_premise": handle_proof_search_alt_hammer_premise,
        }
        response_map = {
            "proof_search_alt.state_search": ProofSearchAltStateSearchResponse,
            "proof_search_alt.hammer_premise": ProofSearchAltHammerPremiseResponse,
        }
        for canonical_name, handler in handler_map.items():
            spec = _TOOL_SPEC_MAP[canonical_name]
            response_type = response_map[canonical_name]
            for alias in aliases_by_canonical.get(canonical_name, ()):
                def _make_proof_alt_tool(current_handler, current_spec, current_response_type):
                    async def _proof_alt_tool(
                        project_root: Annotated[
                            str | None,
                            Field(description=_param_desc(current_spec, "project_root")),
                        ] = None,
                        file_path: Annotated[
                            str,
                            Field(description=_param_desc(current_spec, "file_path")),
                        ] = "",
                        line: Annotated[
                            int,
                            Field(description=_param_desc(current_spec, "line")),
                        ] = 1,
                        column: Annotated[
                            int,
                            Field(description=_param_desc(current_spec, "column")),
                        ] = 1,
                        num_results: Annotated[
                            int | None,
                            Field(description=_param_desc(current_spec, "num_results")),
                        ] = None,
                    ) -> Any:
                        return await run_sync_mcp_service_handler(
                            current_handler,
                            service,
                            prune_none(
                                {
                                    "project_root": project_root,
                                    "file_path": file_path,
                                    "line": line,
                                    "column": column,
                                    "num_results": num_results,
                                }
                            ),
                        )

                    _proof_alt_tool.__annotations__["return"] = current_response_type
                    return _proof_alt_tool

                _proof_alt_tool = _make_proof_alt_tool(handler, spec, response_type)
                mcp.tool(
                    name=alias,
                    description=spec.render_mcp_description(),
                    structured_output=True,
                )(_proof_alt_tool)


__all__ = ["ProofSearchAltGroupPlugin"]
