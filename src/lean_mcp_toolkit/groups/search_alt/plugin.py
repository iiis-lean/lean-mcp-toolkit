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
    with_output_schemas,
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

_BASE_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec("search_alt", "leansearch", "leansearch", "/search_alt/leansearch", "Search Lean declarations via LeanSearch.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "leandex", "leandex", "/search_alt/leandex", "Search Lean declarations via LeanDex.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "loogle", "loogle", "/search_alt/loogle", "Search Lean declarations via Loogle.", _SEARCH_PARAMS, _COMMON_RETURNS),
    GroupToolSpec("search_alt", "leanfinder", "leanfinder", "/search_alt/leanfinder", "Search Lean declarations via LeanFinder.", _SEARCH_PARAMS, _COMMON_RETURNS),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = with_output_schemas(
    _BASE_TOOL_SPECS,
    {
        "leansearch": SearchAltLeanSearchResponse,
        "leandex": SearchAltLeanDexResponse,
        "loogle": SearchAltLoogleResponse,
        "leanfinder": SearchAltLeanFinderResponse,
    },
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
        for alias in aliases_by_canonical.get("leansearch", ()):
            self._register_leansearch(mcp, service=service, alias=alias, prune_none=prune_none)
        for alias in aliases_by_canonical.get("leandex", ()):
            self._register_leandex(mcp, service=service, alias=alias, prune_none=prune_none)
        for alias in aliases_by_canonical.get("loogle", ()):
            self._register_loogle(mcp, service=service, alias=alias, prune_none=prune_none)
        for alias in aliases_by_canonical.get("leanfinder", ()):
            self._register_leanfinder(mcp, service=service, alias=alias, prune_none=prune_none)

    @staticmethod
    def _register_leansearch(mcp: Any, *, service: Any, alias: str, prune_none) -> None:
        spec = _TOOL_SPEC_MAP["leansearch"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _leansearch(
            query: Annotated[
                str,
                Field(description=_param_desc(spec, "query")),
            ] = "",
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> SearchAltLeanSearchResponse:
            return await run_sync_mcp_service_handler(
                handle_search_alt_leansearch,
                service,
                prune_none({"query": query, "num_results": num_results}),
            )

    @staticmethod
    def _register_leandex(mcp: Any, *, service: Any, alias: str, prune_none) -> None:
        spec = _TOOL_SPEC_MAP["leandex"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _leandex(
            query: Annotated[
                str,
                Field(description=_param_desc(spec, "query")),
            ] = "",
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> SearchAltLeanDexResponse:
            return await run_sync_mcp_service_handler(
                handle_search_alt_leandex,
                service,
                prune_none({"query": query, "num_results": num_results}),
            )

    @staticmethod
    def _register_loogle(mcp: Any, *, service: Any, alias: str, prune_none) -> None:
        spec = _TOOL_SPEC_MAP["loogle"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _loogle(
            query: Annotated[
                str,
                Field(description=_param_desc(spec, "query")),
            ] = "",
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> SearchAltLoogleResponse:
            return await run_sync_mcp_service_handler(
                handle_search_alt_loogle,
                service,
                prune_none({"query": query, "num_results": num_results}),
            )

    @staticmethod
    def _register_leanfinder(mcp: Any, *, service: Any, alias: str, prune_none) -> None:
        spec = _TOOL_SPEC_MAP["leanfinder"]

        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
            structured_output=True,
        )
        async def _leanfinder(
            query: Annotated[
                str,
                Field(description=_param_desc(spec, "query")),
            ] = "",
            num_results: Annotated[
                int | None,
                Field(description=_param_desc(spec, "num_results")),
            ] = None,
        ) -> SearchAltLeanFinderResponse:
            return await run_sync_mcp_service_handler(
                handle_search_alt_leanfinder,
                service,
                prune_none({"query": query, "num_results": num_results}),
            )


__all__ = ["SearchAltGroupPlugin"]
