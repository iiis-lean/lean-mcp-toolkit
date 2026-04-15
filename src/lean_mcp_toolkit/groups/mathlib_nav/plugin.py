"""mathlib_nav group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import (
    handle_search_mathlib_nav_file_outline,
    handle_search_mathlib_nav_grep,
    handle_search_mathlib_nav_read,
    handle_search_mathlib_nav_tree,
)
from ...backends.context import BackendContext
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...contracts.mathlib_nav import (
    MathlibNavFileOutlineResponse,
    MathlibNavGrepResponse,
    MathlibNavReadResponse,
    MathlibNavTreeResponse,
)
from ...transport.http import HttpConfig
from .factory import create_mathlib_nav_client, create_mathlib_nav_service
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
    ToolParamSpec("project_root", "str | null", "Lean project root directory.", False, "server default project root"),
    ToolParamSpec("mathlib_root", "str | null", "Optional explicit Mathlib root or repo root containing Mathlib/.", False, "null"),
    ToolParamSpec("base", "str | null", "Base module/path to list from under Mathlib root.", False, "mathlib root"),
    ToolParamSpec("depth", "int | null", "Tree traversal depth.", False, "1"),
    ToolParamSpec("name_filter", "str | null", "Optional name filter.", False, "null"),
    ToolParamSpec("limit", "int | null", "Max entries in page.", False, "search_nav.default_limit"),
    ToolParamSpec("offset", "int | null", "Page offset.", False, "0"),
)

_FILE_OUTLINE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("project_root", "str | null", "Lean project root directory.", False, "server default project root"),
    ToolParamSpec("mathlib_root", "str | null", "Optional explicit Mathlib root or repo root containing Mathlib/.", False, "null"),
    ToolParamSpec("target", "str", "Target Lean file path or module path under Mathlib root.", True),
    ToolParamSpec("include_imports", "bool | null", "Include import list.", False, "search_nav.outline_include_imports_default"),
    ToolParamSpec("include_module_doc", "bool | null", "Include module doc block.", False, "search_nav.outline_include_module_doc_default"),
    ToolParamSpec("include_section_doc", "bool | null", "Include section docs.", False, "search_nav.outline_include_section_doc_default"),
    ToolParamSpec("include_decl_headers", "bool | null", "Include declaration header list.", False, "search_nav.outline_include_decl_headers_default"),
    ToolParamSpec("include_scope_cmds", "bool | null", "Include scope command list.", False, "search_nav.outline_include_scope_cmds_default"),
    ToolParamSpec("limit_decls", "int | null", "Max declaration entries.", False, "search_nav.outline_default_limit_decls"),
)

_READ_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("project_root", "str | null", "Lean project root directory.", False, "server default project root"),
    ToolParamSpec("mathlib_root", "str | null", "Optional explicit Mathlib root or repo root containing Mathlib/.", False, "null"),
    ToolParamSpec("target", "str", "Target Lean file path or module path under Mathlib root.", True),
    ToolParamSpec("start_line", "int | null", "Start line (1-based).", False, "1"),
    ToolParamSpec("end_line", "int | null", "End line (1-based).", False, "null"),
    ToolParamSpec("max_lines", "int | null", "Maximum lines to return.", False, "search_nav.read_default_max_lines"),
    ToolParamSpec("with_line_numbers", "bool | null", "Attach line numbers in output content.", False, "search_nav.read_with_line_numbers_default"),
)

_GREP_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec("project_root", "str | null", "Lean project root directory.", False, "server default project root"),
    ToolParamSpec("mathlib_root", "str | null", "Optional explicit Mathlib root or repo root containing Mathlib/.", False, "null"),
    ToolParamSpec("query", "str", "Text or regex query.", True),
    ToolParamSpec("match_mode", "phrase | word | regex", "Text match strategy.", False, "phrase"),
    ToolParamSpec("base", "str | null", "Optional Mathlib subdirectory/module prefix to search under.", False, "null"),
    ToolParamSpec("target", "str | null", "Optional Mathlib file/module target to search within.", False, "null"),
    ToolParamSpec("context_lines", "int | null", "Snippet context lines.", False, "1"),
    ToolParamSpec("limit", "int | null", "Max results.", False, "search_nav.default_limit"),
    ToolParamSpec("scopes", "list[str] | str | null", "Scopes to scan.", False, "[decl_header, decl_sig, body, comment]"),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="mathlib_nav",
        canonical_name="mathlib_nav.tree",
        raw_name="mathlib_nav.tree",
        api_path="/search/mathlib_nav/tree",
        description="List Mathlib tree entries from a base path/module.",
        params=_TREE_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("resolution", "RepoNavResolution | null", "Resolved root/base info."),
            ToolReturnSpec("entries", "list[RepoNavTreeEntry]", "Tree entries."),
            ToolReturnSpec("page", "RepoNavTreePage | null", "Pagination info."),
        ),
    ),
    GroupToolSpec(
        group_name="mathlib_nav",
        canonical_name="mathlib_nav.file_outline",
        raw_name="mathlib_nav.file_outline",
        api_path="/search/mathlib_nav/file_outline",
        description="Read structured Mathlib file outline (imports/docs/declarations/scope commands).",
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
        group_name="mathlib_nav",
        canonical_name="mathlib_nav.read",
        raw_name="mathlib_nav.read",
        api_path="/search/mathlib_nav/read",
        description="Read Mathlib file content window with optional line numbers.",
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
        group_name="mathlib_nav",
        canonical_name="mathlib_nav.grep",
        raw_name="mathlib_nav.grep",
        api_path="/search/mathlib_nav/grep",
        description="Grep Mathlib source text with grep-like defaults.",
        params=_GREP_PARAMS,
        returns=(
            ToolReturnSpec("success", "bool", "Whether execution succeeded."),
            ToolReturnSpec("error_message", "str | null", "Error details when failed."),
            ToolReturnSpec("query", "str", "Resolved query string."),
            ToolReturnSpec("match_mode", "str", "Resolved text match mode."),
            ToolReturnSpec("count", "int", "Returned item count."),
            ToolReturnSpec("items", "list[LocalTextFindItem]", "Text matches."),
        ),
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


@dataclass(slots=True, frozen=True)
class MathlibNavGroupPlugin(GroupPlugin):
    group_name: str = "mathlib_nav"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        _ = backends
        return create_mathlib_nav_service(config=config)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_mathlib_nav_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "mathlib_nav.tree": lambda payload: handle_search_mathlib_nav_tree(service, payload),
            "mathlib_nav.file_outline": (
                lambda payload: handle_search_mathlib_nav_file_outline(service, payload)
            ),
            "mathlib_nav.read": lambda payload: handle_search_mathlib_nav_read(service, payload),
            "mathlib_nav.grep": lambda payload: handle_search_mathlib_nav_grep(service, payload),
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

        for alias in aliases_by_canonical.get("mathlib_nav.tree", ()):
            spec = _TOOL_SPEC_MAP["mathlib_nav.tree"]

            @mcp.tool(
                name=alias,
                description=spec.render_mcp_description(),
                structured_output=True,
            )
            async def _mathlib_nav_tree(
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                mathlib_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "mathlib_root")),
                ] = None,
                base: Annotated[str | None, Field(description=_param_desc(spec, "base"))] = None,
                depth: Annotated[int | None, Field(description=_param_desc(spec, "depth"))] = None,
                name_filter: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "name_filter")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                offset: Annotated[int | None, Field(description=_param_desc(spec, "offset"))] = None,
            ) -> MathlibNavTreeResponse:
                payload = prune_none(
                    {
                        "project_root": project_root,
                        "mathlib_root": mathlib_root,
                        "base": base,
                        "depth": depth,
                        "name_filter": name_filter,
                        "limit": limit,
                        "offset": offset,
                    }
                )
                return await run_sync_mcp_service_handler(
                    handle_search_mathlib_nav_tree,
                    service,
                    payload,
                )

        for alias in aliases_by_canonical.get("mathlib_nav.file_outline", ()):
            spec = _TOOL_SPEC_MAP["mathlib_nav.file_outline"]

            @mcp.tool(
                name=alias,
                description=spec.render_mcp_description(),
                structured_output=True,
            )
            async def _mathlib_nav_file_outline(
                target: Annotated[str, Field(description=_param_desc(spec, "target"))],
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                mathlib_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "mathlib_root")),
                ] = None,
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
            ) -> MathlibNavFileOutlineResponse:
                payload = prune_none(
                    {
                        "project_root": project_root,
                        "mathlib_root": mathlib_root,
                        "target": target,
                        "include_imports": include_imports,
                        "include_module_doc": include_module_doc,
                        "include_section_doc": include_section_doc,
                        "include_decl_headers": include_decl_headers,
                        "include_scope_cmds": include_scope_cmds,
                        "limit_decls": limit_decls,
                    }
                )
                return await run_sync_mcp_service_handler(
                    handle_search_mathlib_nav_file_outline,
                    service,
                    payload,
                )

        for alias in aliases_by_canonical.get("mathlib_nav.read", ()):
            spec = _TOOL_SPEC_MAP["mathlib_nav.read"]

            @mcp.tool(
                name=alias,
                description=spec.render_mcp_description(),
                structured_output=True,
            )
            async def _mathlib_nav_read(
                target: Annotated[str, Field(description=_param_desc(spec, "target"))],
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                mathlib_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "mathlib_root")),
                ] = None,
                start_line: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "start_line")),
                ] = None,
                end_line: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "end_line")),
                ] = None,
                max_lines: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "max_lines")),
                ] = None,
                with_line_numbers: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "with_line_numbers")),
                ] = None,
            ) -> MathlibNavReadResponse:
                payload = prune_none(
                    {
                        "project_root": project_root,
                        "mathlib_root": mathlib_root,
                        "target": target,
                        "start_line": start_line,
                        "end_line": end_line,
                        "max_lines": max_lines,
                        "with_line_numbers": with_line_numbers,
                    }
                )
                return await run_sync_mcp_service_handler(
                    handle_search_mathlib_nav_read,
                    service,
                    payload,
                )

        for alias in aliases_by_canonical.get("mathlib_nav.grep", ()):
            spec = _TOOL_SPEC_MAP["mathlib_nav.grep"]

            @mcp.tool(
                name=alias,
                description=spec.render_mcp_description(),
                structured_output=True,
            )
            async def _mathlib_nav_grep(
                query: Annotated[str, Field(description=_param_desc(spec, "query"))],
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                mathlib_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "mathlib_root")),
                ] = None,
                match_mode: Annotated[
                    str,
                    Field(description=_param_desc(spec, "match_mode")),
                ] = "phrase",
                base: Annotated[str | None, Field(description=_param_desc(spec, "base"))] = None,
                target: Annotated[str | None, Field(description=_param_desc(spec, "target"))] = None,
                context_lines: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "context_lines")),
                ] = None,
                limit: Annotated[int | None, Field(description=_param_desc(spec, "limit"))] = None,
                scopes: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "scopes")),
                ] = None,
            ) -> MathlibNavGrepResponse:
                payload = prune_none(
                    {
                        "project_root": project_root,
                        "mathlib_root": mathlib_root,
                        "query": query,
                        "match_mode": match_mode,
                        "base": base,
                        "target": target,
                        "context_lines": context_lines,
                        "limit": limit,
                        "scopes": scopes,
                    }
                )
                return await run_sync_mcp_service_handler(
                    handle_search_mathlib_nav_grep,
                    service,
                    payload,
                )


__all__ = ["MathlibNavGroupPlugin"]
