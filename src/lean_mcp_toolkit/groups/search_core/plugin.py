"""search_core group plugin."""

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
    handle_search_local_decl_search,
    handle_search_mathlib_decl_get,
    handle_search_mathlib_decl_search,
)
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from .factory import create_search_core_client, create_search_core_service
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
)


_SEARCH_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="query",
        type_hint="str",
        required=True,
        description="Search query by declaration name fragment or mathematical meaning.",
    ),
    ToolParamSpec(
        name="limit",
        type_hint="int | null",
        required=False,
        default_value="search_core.default_limit",
        description="Maximum number of results to return.",
    ),
    ToolParamSpec(
        name="rerank_top",
        type_hint="int | null",
        required=False,
        default_value="search_core.default_rerank_top",
        description="Number of retrieved candidates to rerank.",
    ),
    ToolParamSpec(
        name="packages",
        type_hint="list[str] | str | null",
        required=False,
        default_value="search_core.default_packages",
        description="Optional package filter, e.g. ['Mathlib'].",
    ),
    ToolParamSpec(
        name="include_module",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration module path.",
    ),
    ToolParamSpec(
        name="include_docstring",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration docstring field.",
    ),
    ToolParamSpec(
        name="include_source_text",
        type_hint="bool",
        required=False,
        default_value="false",
        description="Include declaration Lean source text.",
    ),
    ToolParamSpec(
        name="include_source_link",
        type_hint="bool",
        required=False,
        default_value="false",
        description="Include declaration source link.",
    ),
    ToolParamSpec(
        name="include_dependencies",
        type_hint="bool",
        required=False,
        default_value="false",
        description="Include declaration dependency summary field.",
    ),
    ToolParamSpec(
        name="include_informalization",
        type_hint="bool",
        required=False,
        default_value="false",
        description="Include declaration natural-language informalization.",
    ),
)

_GET_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="declaration_id",
        type_hint="int",
        required=True,
        description="Declaration id returned by search.mathlib_decl.search.",
    ),
    ToolParamSpec(
        name="include_module",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration module path.",
    ),
    ToolParamSpec(
        name="include_docstring",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration docstring field.",
    ),
    ToolParamSpec(
        name="include_source_text",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration Lean source text.",
    ),
    ToolParamSpec(
        name="include_source_link",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration source link.",
    ),
    ToolParamSpec(
        name="include_dependencies",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration dependency summary field.",
    ),
    ToolParamSpec(
        name="include_informalization",
        type_hint="bool",
        required=False,
        default_value="true",
        description="Include declaration natural-language informalization.",
    ),
)

_LOCAL_SEARCH_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="query",
        type_hint="str",
        required=True,
        description="Declaration name or prefix to search in local Lean files.",
    ),
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description="Lean project root directory for local search scope.",
    ),
    ToolParamSpec(
        name="limit",
        type_hint="int | null",
        required=False,
        default_value="search_core.local_decl_default_limit",
        description="Maximum number of local declaration matches.",
    ),
    ToolParamSpec(
        name="include_dependencies",
        type_hint="bool | null",
        required=False,
        default_value="search_core.local_decl_include_dependencies",
        description="Whether to include .lake/packages declarations.",
    ),
    ToolParamSpec(
        name="include_stdlib",
        type_hint="bool | null",
        required=False,
        default_value="search_core.local_decl_include_stdlib",
        description="Whether to include Lean stdlib declarations.",
    ),
)

_MATHLIB_ITEM_FIELDS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("id", "int", "Declaration id."),
    ToolReturnSpec("name", "str", "Declaration full name."),
    ToolReturnSpec("module", "str | null", "Declaration module."),
    ToolReturnSpec("docstring", "str | null", "Declaration docstring."),
    ToolReturnSpec("source_text", "str | null", "Lean source text."),
    ToolReturnSpec("source_link", "str | null", "Source link."),
    ToolReturnSpec("dependencies", "str | null", "Dependencies payload."),
    ToolReturnSpec("informalization", "str | null", "Natural-language description."),
)

_SEARCH_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("query", "str", "Resolved query string."),
    ToolReturnSpec("count", "int", "Returned result count."),
    ToolReturnSpec("processing_time_ms", "int | null", "Backend processing time."),
    ToolReturnSpec(
        "results",
        "list[MathlibDeclSummaryItem]",
        "Search result items.",
        children=_MATHLIB_ITEM_FIELDS,
    ),
)

_GET_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("found", "bool", "Whether declaration id was found."),
    ToolReturnSpec(
        "item",
        "MathlibDeclSummaryItem | null",
        "Detail item for the requested declaration id.",
        children=_MATHLIB_ITEM_FIELDS,
    ),
)

_LOCAL_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("query", "str", "Resolved query string."),
    ToolReturnSpec("count", "int", "Returned result count."),
    ToolReturnSpec(
        "items",
        "list[LocalDeclSearchItem]",
        "Local declaration matches.",
        children=(
            ToolReturnSpec("name", "str", "Declaration name."),
            ToolReturnSpec("kind", "str", "Declaration kind token."),
            ToolReturnSpec("file", "str", "Source file path."),
            ToolReturnSpec("origin", "project | dependency | stdlib", "Source origin."),
        ),
    ),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="search_core",
        canonical_name="search.mathlib_decl.search",
        raw_name="mathlib_decl.search",
        api_path="/search/mathlib_decl/search",
        description="Search declaration index (LeanExplore backend) and return summary items.",
        params=_SEARCH_PARAMS,
        returns=_SEARCH_RETURNS,
    ),
    GroupToolSpec(
        group_name="search_core",
        canonical_name="search.mathlib_decl.get",
        raw_name="mathlib_decl.get",
        api_path="/search/mathlib_decl/get",
        description="Get one declaration detail by declaration id.",
        params=_GET_PARAMS,
        returns=_GET_RETURNS,
    ),
    GroupToolSpec(
        group_name="search_core",
        canonical_name="search.local_decl.search",
        raw_name="local_decl.search",
        api_path="/search/local_decl/search",
        description="Fast local declaration-name search in project/dependency/stdlib Lean files.",
        params=_LOCAL_SEARCH_PARAMS,
        returns=_LOCAL_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class SearchCoreGroupPlugin(GroupPlugin):
    group_name: str = "search_core"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LEAN_EXPLORE_BACKEND,)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_search_core_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_search_core_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "search.mathlib_decl.search": (
                lambda payload: handle_search_mathlib_decl_search(service, payload)
            ),
            "search.mathlib_decl.get": (
                lambda payload: handle_search_mathlib_decl_get(service, payload)
            ),
            "search.local_decl.search": (
                lambda payload: handle_search_local_decl_search(service, payload)
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
        search_spec = _TOOL_SPEC_MAP["search.mathlib_decl.search"]
        get_spec = _TOOL_SPEC_MAP["search.mathlib_decl.get"]
        local_spec = _TOOL_SPEC_MAP["search.local_decl.search"]

        for alias in aliases_by_canonical.get("search.mathlib_decl.search", ()): 
            self._register_mathlib_search(
                mcp=mcp,
                alias=alias,
                spec=search_spec,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("search.mathlib_decl.get", ()): 
            self._register_mathlib_get(
                mcp=mcp,
                alias=alias,
                spec=get_spec,
                service=service,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("search.local_decl.search", ()): 
            self._register_local_search(
                mcp=mcp,
                alias=alias,
                spec=local_spec,
                service=service,
                prune_none=prune_none,
            )

    @staticmethod
    def _register_mathlib_search(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(name=alias, description=spec.render_mcp_description())
        def _search_mathlib_decl_search(
            query: Annotated[str, Field(description=_param_desc(spec, "query"))],
            limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
            rerank_top: Annotated[
                int | None,
                Field(description=_param_desc(spec, "rerank_top")),
            ] = None,
            packages: Annotated[
                list[str] | str | None,
                Field(description=_param_desc(spec, "packages")),
            ] = None,
            include_module: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_module")),
            ] = True,
            include_docstring: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_docstring")),
            ] = True,
            include_source_text: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_source_text")),
            ] = False,
            include_source_link: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_source_link")),
            ] = False,
            include_dependencies: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_dependencies")),
            ] = False,
            include_informalization: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_informalization")),
            ] = False,
        ) -> JsonDict:
            payload = {
                "query": query,
                "limit": limit,
                "rerank_top": rerank_top,
                "packages": normalize_str_list(packages),
                "include_module": include_module,
                "include_docstring": include_docstring,
                "include_source_text": include_source_text,
                "include_source_link": include_source_link,
                "include_dependencies": include_dependencies,
                "include_informalization": include_informalization,
            }
            return handle_search_mathlib_decl_search(service, prune_none(payload))

    @staticmethod
    def _register_mathlib_get(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        @mcp.tool(name=alias, description=spec.render_mcp_description())
        def _search_mathlib_decl_get(
            declaration_id: Annotated[int, Field(description=_param_desc(spec, "declaration_id"))],
            include_module: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_module")),
            ] = True,
            include_docstring: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_docstring")),
            ] = True,
            include_source_text: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_source_text")),
            ] = True,
            include_source_link: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_source_link")),
            ] = True,
            include_dependencies: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_dependencies")),
            ] = True,
            include_informalization: Annotated[
                bool,
                Field(description=_param_desc(spec, "include_informalization")),
            ] = True,
        ) -> JsonDict:
            payload = {
                "declaration_id": declaration_id,
                "include_module": include_module,
                "include_docstring": include_docstring,
                "include_source_text": include_source_text,
                "include_source_link": include_source_link,
                "include_dependencies": include_dependencies,
                "include_informalization": include_informalization,
            }
            return handle_search_mathlib_decl_get(service, prune_none(payload))

    @staticmethod
    def _register_local_search(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        @mcp.tool(name=alias, description=spec.render_mcp_description())
        def _search_local_decl_search(
            query: Annotated[str, Field(description=_param_desc(spec, "query"))],
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
            include_dependencies: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "include_dependencies")),
            ] = None,
            include_stdlib: Annotated[
                bool | None,
                Field(description=_param_desc(spec, "include_stdlib")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "query": query,
                "project_root": project_root,
                "limit": limit,
                "include_dependencies": include_dependencies,
                "include_stdlib": include_stdlib,
            }
            return handle_search_local_decl_search(service, prune_none(payload))


__all__ = ["SearchCoreGroupPlugin"]
