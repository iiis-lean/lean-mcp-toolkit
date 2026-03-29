"""search_nav group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_search_local_decl_find,
    handle_search_local_import_find,
    handle_search_local_refs_find,
    handle_search_local_scope_find,
    handle_search_local_text_find,
    handle_search_repo_nav_file_outline,
    handle_search_repo_nav_read,
    handle_search_repo_nav_tree,
)
from ...backends.context import BackendContext
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from .factory import create_search_nav_client, create_search_nav_service
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
    run_sync_mcp_service_handler,
)


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for p in spec.params:
        if p.name == name:
            return p.description
    return ""


_TREE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("base", "str | null", "Base module/path to list from.", False, "repo root"),
    ToolParamSpec("depth", "int | null", "Tree traversal depth.", False, "1"),
    ToolParamSpec("name_filter", "str | null", "Optional name filter.", False, "null"),
    ToolParamSpec("limit", "int | null", "Max entries in page.", False, "search_nav.default_limit"),
    ToolParamSpec("offset", "int | null", "Page offset.", False, "0"),
)

_FILE_OUTLINE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("target", "str", "Target Lean file path or module path.", True),
    ToolParamSpec("include_imports", "bool | null", "Include import list.", False, "search_nav.outline_include_imports_default"),
    ToolParamSpec("include_module_doc", "bool | null", "Include module doc block.", False, "search_nav.outline_include_module_doc_default"),
    ToolParamSpec("include_section_doc", "bool | null", "Include section docs.", False, "search_nav.outline_include_section_doc_default"),
    ToolParamSpec("include_decl_headers", "bool | null", "Include declaration header list.", False, "search_nav.outline_include_decl_headers_default"),
    ToolParamSpec("include_scope_cmds", "bool | null", "Include scope command list.", False, "search_nav.outline_include_scope_cmds_default"),
    ToolParamSpec("limit_decls", "int | null", "Max declaration entries.", False, "search_nav.outline_default_limit_decls"),
)

_READ_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("target", "str", "Target Lean file path or module path.", True),
    ToolParamSpec("start_line", "int | null", "Start line (1-based).", False, "1"),
    ToolParamSpec("end_line", "int | null", "End line (1-based).", False, "null"),
    ToolParamSpec("max_lines", "int | null", "Maximum lines to return.", False, "search_nav.read_default_max_lines"),
    ToolParamSpec("with_line_numbers", "bool | null", "Attach line numbers in output content.", False, "search_nav.read_with_line_numbers_default"),
)

_LOCAL_DECL_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("query", "str", "Declaration query.", True),
    ToolParamSpec("match_mode", "exact | prefix | suffix", "Declaration name match mode.", False, "prefix"),
    ToolParamSpec("decl_kinds", "list[str] | str | null", "Optional declaration kind filter.", False, "null"),
    ToolParamSpec("namespace_filter", "str | null", "Namespace prefix filter.", False, "null"),
    ToolParamSpec("module_filter", "str | null", "Module prefix filter.", False, "null"),
    ToolParamSpec("include_deps", "bool | null", "Whether to scan dependencies under .lake/packages.", False, "search_nav.include_deps_default"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
)

_LOCAL_IMPORT_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("query", "str", "Module query.", True),
    ToolParamSpec("match_mode", "exact | prefix | suffix", "Module match mode.", False, "exact"),
    ToolParamSpec("direction", "imports | imported_by", "Edge direction.", False, "imported_by"),
    ToolParamSpec("module_filter", "str | null", "Importer-module prefix filter.", False, "null"),
    ToolParamSpec("include_deps", "bool | null", "Whether to scan dependencies.", False, "search_nav.include_deps_default"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
)

_LOCAL_SCOPE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("query", "str | null", "Optional scope-target query.", False, "null"),
    ToolParamSpec("scope_kinds", "list[str] | str | null", "Scope kinds filter.", False, "[namespace, section, open, open_scoped, export, attribute]"),
    ToolParamSpec("match_mode", "exact | prefix | suffix", "Target match mode.", False, "prefix"),
    ToolParamSpec("module_filter", "str | null", "Module prefix filter.", False, "null"),
    ToolParamSpec("include_deps", "bool | null", "Whether to scan dependencies.", False, "search_nav.include_deps_default"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
    ToolParamSpec("context_lines", "int | null", "Snippet context lines.", False, "search_nav.default_context_lines"),
)

_LOCAL_TEXT_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("query", "str", "Text query.", True),
    ToolParamSpec("scopes", "list[str] | str | null", "Text scopes filter.", False, "[module_doc, section_doc, decl_doc, decl_header, decl_sig]"),
    ToolParamSpec("text_match", "phrase | word | regex", "Text match strategy.", False, "phrase"),
    ToolParamSpec("module_filter", "str | null", "Module prefix filter.", False, "null"),
    ToolParamSpec("include_deps", "bool | null", "Whether to scan dependencies.", False, "search_nav.include_deps_default"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
    ToolParamSpec("context_lines", "int | null", "Snippet context lines.", False, "search_nav.default_context_lines"),
)

_LOCAL_REFS_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("repo_root", "str | null", "Lean project/repo root.", False, "server default project root"),
    ToolParamSpec("symbol", "str", "Symbol to find references for.", True),
    ToolParamSpec("include_definition_site", "bool | null", "Include definition location in results.", False, "search_nav.refs_include_definition_default"),
    ToolParamSpec("scopes", "list[str] | str | null", "Reference scopes filter.", False, "[decl_header, import, scope_cmd, body]"),
    ToolParamSpec("module_filter", "str | null", "Module prefix filter.", False, "null"),
    ToolParamSpec("include_deps", "bool | null", "Whether to scan dependencies.", False, "search_nav.include_deps_default"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
    ToolParamSpec("context_lines", "int | null", "Snippet context lines.", False, "search_nav.default_context_lines"),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.repo_nav.tree",
        raw_name="repo_nav.tree",
        api_path="/search/repo_nav/tree",
        description="List Lean repo tree entries from base path/module.",
        params=_TREE_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("resolution", "RepoNavResolution | null", "Resolved base info."),
            ToolReturnSpec("entries", "list[RepoNavTreeEntry]", "Tree entries."),
            ToolReturnSpec("page", "RepoNavTreePage | null", "Pagination info."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.repo_nav.file_outline",
        raw_name="repo_nav.file_outline",
        api_path="/search/repo_nav/file_outline",
        description="Read structured file outline (imports/docs/declarations/scope commands).",
        params=_FILE_OUTLINE_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("target", "RepoNavTarget | null", "Resolved target info."),
            ToolReturnSpec("imports", "list[str]", "Import module list."),
            ToolReturnSpec("module_doc", "str | null", "Module doc block."),
            ToolReturnSpec("sections", "list[RepoNavSectionItem]", "Section docs."),
            ToolReturnSpec("declarations", "list[RepoNavDeclarationItem]", "Declaration headers."),
            ToolReturnSpec("scope_cmds", "list[RepoNavScopeCmdItem]", "Scope command list."),
            ToolReturnSpec("summary", "RepoNavOutlineSummary | null", "Outline summary."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.repo_nav.read",
        raw_name="repo_nav.read",
        api_path="/search/repo_nav/read",
        description="Read file content window with optional line numbers.",
        params=_READ_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("target", "RepoNavTarget | null", "Resolved target info."),
            ToolReturnSpec("window", "RepoNavReadWindow | null", "Returned window info."),
            ToolReturnSpec("content", "str", "Window content text."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.local_decl.find",
        raw_name="local_decl.find",
        api_path="/search/local_decl/find",
        description="Find named declarations in local project/dependency Lean sources.",
        params=_LOCAL_DECL_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("query", "str", "Resolved query string."),
            ToolReturnSpec("count", "int", "Returned item count."),
            ToolReturnSpec("items", "list[LocalDeclFindItem]", "Declaration matches."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.local_import.find",
        raw_name="local_import.find",
        api_path="/search/local_import/find",
        description="Find import dependency edges around a module query.",
        params=_LOCAL_IMPORT_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("query", "str", "Resolved query string."),
            ToolReturnSpec("count", "int", "Returned edge count."),
            ToolReturnSpec("edges", "list[LocalImportEdgeItem]", "Import edges."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.local_scope.find",
        raw_name="local_scope.find",
        api_path="/search/local_scope/find",
        description="Find namespace/section/open/export/attribute scope commands.",
        params=_LOCAL_SCOPE_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("count", "int", "Returned item count."),
            ToolReturnSpec("items", "list[LocalScopeFindItem]", "Scope-command matches."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.local_text.find",
        raw_name="local_text.find",
        api_path="/search/local_text/find",
        description="Find text snippets in structured Lean source scopes.",
        params=_LOCAL_TEXT_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("query", "str", "Resolved query string."),
            ToolReturnSpec("count", "int", "Returned item count."),
            ToolReturnSpec("items", "list[LocalTextFindItem]", "Text matches."),
        ),
    ),
    GroupToolSpec(
        group_name="search_nav",
        canonical_name="search.local_refs.find",
        raw_name="local_refs.find",
        api_path="/search/local_refs/find",
        description="Find lightweight symbol references in local Lean source files.",
        params=_LOCAL_REFS_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("symbol", "str", "Resolved symbol."),
            ToolReturnSpec("count", "int", "Returned item count."),
            ToolReturnSpec("items", "list[LocalRefsFindItem]", "Reference matches."),
        ),
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


@dataclass(slots=True, frozen=True)
class SearchNavGroupPlugin(GroupPlugin):
    group_name: str = "search_nav"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        _ = backends
        return create_search_nav_service(config=config)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_search_nav_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "search.repo_nav.tree": lambda payload: handle_search_repo_nav_tree(service, payload),
            "search.repo_nav.file_outline": (
                lambda payload: handle_search_repo_nav_file_outline(service, payload)
            ),
            "search.repo_nav.read": lambda payload: handle_search_repo_nav_read(service, payload),
            "search.local_decl.find": lambda payload: handle_search_local_decl_find(service, payload),
            "search.local_import.find": lambda payload: handle_search_local_import_find(service, payload),
            "search.local_scope.find": lambda payload: handle_search_local_scope_find(service, payload),
            "search.local_text.find": lambda payload: handle_search_local_text_find(service, payload),
            "search.local_refs.find": lambda payload: handle_search_local_refs_find(service, payload),
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

        for alias in aliases_by_canonical.get("search.repo_nav.tree", ()): 
            spec = _TOOL_SPEC_MAP["search.repo_nav.tree"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _repo_nav_tree(
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                base: Annotated[str | None, Field(description=_param_desc(spec, "base"))] = None,
                depth: Annotated[int | None, Field(description=_param_desc(spec, "depth"))] = None,
                name_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "name_filter")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                offset: Annotated[int | None, Field(description=_param_desc(spec, "offset"))] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "base": base,
                    "depth": depth,
                    "name_filter": name_filter,
                    "limit": limit,
                    "offset": offset,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_repo_nav_tree,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.repo_nav.file_outline", ()): 
            spec = _TOOL_SPEC_MAP["search.repo_nav.file_outline"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _repo_nav_file_outline(
                target: Annotated[str, Field(description=_param_desc(spec, "target"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                include_imports: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_imports")),
                ] = None,
                include_module_doc: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_module_doc")),
                ] = None,
                include_section_doc: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_section_doc")),
                ] = None,
                include_decl_headers: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_decl_headers")),
                ] = None,
                include_scope_cmds: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_scope_cmds")),
                ] = None,
                limit_decls: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "limit_decls")),
                ] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "target": target,
                    "include_imports": include_imports,
                    "include_module_doc": include_module_doc,
                    "include_section_doc": include_section_doc,
                    "include_decl_headers": include_decl_headers,
                    "include_scope_cmds": include_scope_cmds,
                    "limit_decls": limit_decls,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_repo_nav_file_outline,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.repo_nav.read", ()): 
            spec = _TOOL_SPEC_MAP["search.repo_nav.read"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _repo_nav_read(
                target: Annotated[str, Field(description=_param_desc(spec, "target"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                start_line: Annotated[int | None, Field(description=_param_desc(spec, "start_line"))] = None,
                end_line: Annotated[int | None, Field(description=_param_desc(spec, "end_line"))] = None,
                max_lines: Annotated[int | None, Field(description=_param_desc(spec, "max_lines"))] = None,
                with_line_numbers: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "with_line_numbers")),
                ] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "target": target,
                    "start_line": start_line,
                    "end_line": end_line,
                    "max_lines": max_lines,
                    "with_line_numbers": with_line_numbers,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_repo_nav_read,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.local_decl.find", ()): 
            spec = _TOOL_SPEC_MAP["search.local_decl.find"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _local_decl_find(
                query: Annotated[str, Field(description=_param_desc(spec, "query"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                match_mode: Annotated[str, Field(description=_param_desc(spec, "match_mode"))] = "prefix",
                decl_kinds: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "decl_kinds")),
                ] = None,
                namespace_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "namespace_filter")),
                ] = None,
                module_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "module_filter")),
                ] = None,
                include_deps: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_deps")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "query": query,
                    "match_mode": match_mode,
                    "decl_kinds": decl_kinds,
                    "namespace_filter": namespace_filter,
                    "module_filter": module_filter,
                    "include_deps": include_deps,
                    "limit": limit,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_local_decl_find,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.local_import.find", ()): 
            spec = _TOOL_SPEC_MAP["search.local_import.find"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _local_import_find(
                query: Annotated[str, Field(description=_param_desc(spec, "query"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                match_mode: Annotated[str, Field(description=_param_desc(spec, "match_mode"))] = "exact",
                direction: Annotated[str, Field(description=_param_desc(spec, "direction"))] = "imported_by",
                module_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "module_filter")),
                ] = None,
                include_deps: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_deps")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "query": query,
                    "match_mode": match_mode,
                    "direction": direction,
                    "module_filter": module_filter,
                    "include_deps": include_deps,
                    "limit": limit,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_local_import_find,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.local_scope.find", ()): 
            spec = _TOOL_SPEC_MAP["search.local_scope.find"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _local_scope_find(
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                query: Annotated[str | None, Field(description=_param_desc(spec, "query"))] = None,
                scope_kinds: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "scope_kinds")),
                ] = None,
                match_mode: Annotated[str, Field(description=_param_desc(spec, "match_mode"))] = "prefix",
                module_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "module_filter")),
                ] = None,
                include_deps: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_deps")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                context_lines: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "context_lines")),
                ] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "query": query,
                    "scope_kinds": scope_kinds,
                    "match_mode": match_mode,
                    "module_filter": module_filter,
                    "include_deps": include_deps,
                    "limit": limit,
                    "context_lines": context_lines,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_local_scope_find,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.local_text.find", ()): 
            spec = _TOOL_SPEC_MAP["search.local_text.find"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _local_text_find(
                query: Annotated[str, Field(description=_param_desc(spec, "query"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                scopes: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "scopes")),
                ] = None,
                text_match: Annotated[str, Field(description=_param_desc(spec, "text_match"))] = "phrase",
                module_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "module_filter")),
                ] = None,
                include_deps: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_deps")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                context_lines: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "context_lines")),
                ] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "query": query,
                    "scopes": scopes,
                    "text_match": text_match,
                    "module_filter": module_filter,
                    "include_deps": include_deps,
                    "limit": limit,
                    "context_lines": context_lines,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_local_text_find,
                    service,
                    prune_none(payload),
                )

        for alias in aliases_by_canonical.get("search.local_refs.find", ()): 
            spec = _TOOL_SPEC_MAP["search.local_refs.find"]

            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _local_refs_find(
                symbol: Annotated[str, Field(description=_param_desc(spec, "symbol"))],
                repo_root: Annotated[str | None, Field(description=_param_desc(spec, "repo_root"))] = None,
                include_definition_site: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_definition_site")),
                ] = None,
                scopes: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "scopes")),
                ] = None,
                module_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "module_filter")),
                ] = None,
                include_deps: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "include_deps")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                context_lines: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "context_lines")),
                ] = None,
            ) -> JsonDict:
                payload = {
                    "repo_root": repo_root,
                    "symbol": symbol,
                    "include_definition_site": include_definition_site,
                    "scopes": scopes,
                    "module_filter": module_filter,
                    "include_deps": include_deps,
                    "limit": limit,
                    "context_lines": context_lines,
                }
                return await run_sync_mcp_service_handler(
                    handle_search_local_refs_find,
                    service,
                    prune_none(payload),
                )


__all__ = ["SearchNavGroupPlugin"]
