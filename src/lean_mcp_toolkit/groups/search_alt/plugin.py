"""search_alt group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_search_alt_leandex,
    handle_search_alt_leanfinder,
    handle_search_alt_leansearch,
    handle_search_alt_loogle,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...contracts.search_alt import (
    SearchAltLeanDexResponse,
    SearchAltLeanFinderResponse,
    SearchAltLeanSearchResponse,
    SearchAltLoogleResponse,
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
from .factory import create_search_alt_client, create_search_alt_service

_SEARCH_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("query", "str", "Natural language or Lean-style query.", required=True),
    ToolParamSpec(
        "num_results",
        "int | null",
        "Maximum results to return.",
        required=False,
        default_value="group default",
    ),
)

_COMMON_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether provider query succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when success=false."),
    ToolReturnSpec("query", "str", "Original query."),
    ToolReturnSpec("provider", "str", "Provider name."),
    ToolReturnSpec("backend_mode", "str", "Backend mode such as remote/local."),
    ToolReturnSpec("items", "list[...]", "Result items."),
    ToolReturnSpec("count", "int", "Number of result items."),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec("search_alt", "leansearch", "leansearch", "/search_alt/leansearch", "Search Lean declarations via LeanSearch.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "leandex", "leandex", "/search_alt/leandex", "Search Lean declarations via LeanDex.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "loogle", "loogle", "/search_alt/loogle", "Search Lean declarations via Loogle.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "leanfinder", "leanfinder", "/search_alt/leanfinder", "Search Lean declarations via LeanFinder.", _SEARCH_PARAMS, _COMMON_RETURNS),
)

_TOOL_SPEC_MAP = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class SearchAltGroupPlugin(GroupPlugin):
    group_name: str = "search_alt"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.SEARCH_ALT_MANAGER,)

    def create_local_service(self, config: ToolkitConfig, *, backends: BackendContext | None = None):
        return create_search_alt_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_search_alt_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "leansearch": lambda payload: handle_search_alt_leansearch(service, payload),
            "leandex": lambda payload: handle_search_alt_leandex(service, payload),
            "loogle": lambda payload: handle_search_alt_loogle(service, payload),
            "leanfinder": lambda payload: handle_search_alt_leanfinder(service, payload),
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
            "leansearch": handle_search_alt_leansearch,
            "leandex": handle_search_alt_leandex,
            "loogle": handle_search_alt_loogle,
            "leanfinder": handle_search_alt_leanfinder,
        }
        response_map = {
            "leansearch": SearchAltLeanSearchResponse,
            "leandex": SearchAltLeanDexResponse,
            "loogle": SearchAltLoogleResponse,
            "leanfinder": SearchAltLeanFinderResponse,
        }
        for canonical_name, handler in handler_map.items():
            spec = _TOOL_SPEC_MAP[canonical_name]
            response_type = response_map[canonical_name]
            for alias in aliases_by_canonical.get(canonical_name, ()):
                def _make_search_alt_tool(current_handler, current_spec, current_response_type):
                    async def _search_alt_tool(
                        query: Annotated[
                            str,
                            Field(description=_param_desc(current_spec, "query")),
                        ] = "",
                        num_results: Annotated[
                            int | None,
                            Field(description=_param_desc(current_spec, "num_results")),
                        ] = None,
                    ) -> Any:
                        return await run_sync_mcp_service_handler(
                            current_handler,
                            service,
                            prune_none({"query": query, "num_results": num_results}),
                        )

                    _search_alt_tool.__annotations__["return"] = current_response_type
                    return _search_alt_tool

                _search_alt_tool = _make_search_alt_tool(handler, spec, response_type)
                mcp.tool(
                    name=alias,
                    description=spec.render_mcp_description(),
                    structured_output=True,
                )(_search_alt_tool)


__all__ = ["SearchAltGroupPlugin"]
