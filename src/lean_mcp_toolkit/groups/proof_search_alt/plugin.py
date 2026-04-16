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
    with_output_schemas,
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

_BASE_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec("proof_search_alt", "proof_search_alt.state_search", "state_search", "/proof_search_alt/state_search", "Search lemmas by current goal state.", _COMMON_PARAMS, _RETURNS),
    GroupToolSpec("proof_search_alt", "proof_search_alt.hammer_premise", "hammer_premise", "/proof_search_alt/hammer_premise", "Retrieve premise suggestions for current goal.", _COMMON_PARAMS, _RETURNS),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = with_output_schemas(
    _BASE_TOOL_SPECS,
    {
        "proof_search_alt.state_search": ProofSearchAltStateSearchResponse,
        "proof_search_alt.hammer_premise": ProofSearchAltHammerPremiseResponse,
    },
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
        for alias in aliases_by_canonical.get("proof_search_alt.state_search", ()):
            self._register_state_search(mcp, service=service, alias=alias, prune_none=prune_none)
        for alias in aliases_by_canonical.get("proof_search_alt.hammer_premise", ()):
            self._register_hammer_premise(
                mcp,
                service=service,
                alias=alias,
                prune_none=prune_none,
            )

    @staticmethod
    def _register_state_search(mcp: Any, *, service: Any, alias: str, prune_none) -> None:
        spec = _TOOL_SPEC_MAP["proof_search_alt.state_search"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _state_search(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            file_path: Annotated[
                str,
                Field(description=_param_desc(spec, "file_path")),
            ] = "",
            line: Annotated[
                int,
                Field(description=_param_desc(spec, "line")),
            ] = 1,
            column: Annotated[
                int,
                Field(description=_param_desc(spec, "column")),
            ] = 1,
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> ProofSearchAltStateSearchResponse:
            return await run_sync_mcp_service_handler(
                handle_proof_search_alt_state_search,
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

    @staticmethod
    def _register_hammer_premise(
        mcp: Any,
        *,
        service: Any,
        alias: str,
        prune_none,
    ) -> None:
        spec = _TOOL_SPEC_MAP["proof_search_alt.hammer_premise"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _hammer_premise(
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            file_path: Annotated[
                str,
                Field(description=_param_desc(spec, "file_path")),
            ] = "",
            line: Annotated[
                int,
                Field(description=_param_desc(spec, "line")),
            ] = 1,
            column: Annotated[
                int,
                Field(description=_param_desc(spec, "column")),
            ] = 1,
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> ProofSearchAltHammerPremiseResponse:
            return await run_sync_mcp_service_handler(
                handle_proof_search_alt_hammer_premise,
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


__all__ = ["ProofSearchAltGroupPlugin"]
