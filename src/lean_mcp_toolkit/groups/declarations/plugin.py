"""Declarations group plugin."""

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover - optional runtime dependency

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import handle_declarations_extract, handle_declarations_locate
from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from .factory import create_declarations_client, create_declarations_service
from ..plugin_base import (
    GroupPlugin,
    GroupToolSpec,
    ToolHandler,
    ToolParamSpec,
    ToolReturnSpec,
    run_sync_mcp_service_handler,
)

_EXTRACT_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description=(
            "Lean project root directory. If not provided, server default root is used."
        ),
    ),
    ToolParamSpec(
        name="target",
        type_hint="str",
        required=True,
        description=(
            "Single target Lean file to extract declarations from. "
            "Supports Lean dot path, relative .lean path, or absolute .lean path under project root."
        ),
    ),
)

_LOCATE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description=(
            "Lean project root directory. If not provided, server default root is used."
        ),
    ),
    ToolParamSpec(
        name="source_file",
        type_hint="str",
        required=True,
        description=(
            "Lean source file where the symbol appears. "
            "Supports Lean dot path, relative .lean path, or absolute .lean path under project root."
        ),
    ),
    ToolParamSpec(
        name="symbol",
        type_hint="str",
        required=True,
        description="Symbol string to locate from source_file context.",
    ),
    ToolParamSpec(
        name="line",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Optional 0-based line for precise source symbol position.",
    ),
    ToolParamSpec(
        name="column",
        type_hint="int | null",
        required=False,
        default_value="null",
        description="Optional 0-based column for precise source symbol position.",
    ),
)

_EXTRACT_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether declaration extraction succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when extraction fails."),
    ToolReturnSpec("total_declarations", "int", "Number of declarations in response."),
    ToolReturnSpec(
        "declarations",
        "list[DeclarationItem]",
        "Extracted declarations.",
        children=(
            ToolReturnSpec("name", "str", "Declaration name."),
            ToolReturnSpec("kind", "str | null", "Declaration kind, if backend provides it."),
            ToolReturnSpec(
                "signature",
                "str | null",
                "Declaration signature text sliced from source by signature range.",
            ),
            ToolReturnSpec(
                "value",
                "str | null",
                "Declaration value/body text sliced from source by value range.",
            ),
            ToolReturnSpec(
                "full_declaration",
                "str | null",
                "Complete declaration text sliced from source by declaration range.",
            ),
            ToolReturnSpec(
                "docstring",
                "str | null",
                "Declaration docstring text, if present.",
            ),
            ToolReturnSpec(
                "decl_start_pos",
                "Position | null",
                "Declaration start position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "decl_end_pos",
                "Position | null",
                "Declaration end position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "doc_start_pos",
                "Position | null",
                "Docstring start position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "doc_end_pos",
                "Position | null",
                "Docstring end position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
        ),
    ),
)

_LOCATE_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether declaration locate succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure detail when locate fails."),
    ToolReturnSpec(
        "source_pos",
        "Position | null",
        "Resolved source symbol position (0-based).",
        children=(
            ToolReturnSpec("line", "int", "Line number."),
            ToolReturnSpec("column", "int", "Column number."),
        ),
    ),
    ToolReturnSpec(
        "target_file_path",
        "str | null",
        "Absolute target file path from LSP locate result.",
    ),
    ToolReturnSpec(
        "target_range",
        "Range | null",
        "Target token range from LSP locate result (0-based).",
        children=(
            ToolReturnSpec(
                "start",
                "Position",
                "Range start position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "end",
                "Position",
                "Range end position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
        ),
    ),
    ToolReturnSpec(
        "matched_declaration",
        "DeclarationItem | null",
        "Matched declaration extracted from target file.",
        children=(
            ToolReturnSpec("name", "str", "Declaration name."),
            ToolReturnSpec("kind", "str | null", "Declaration kind, if backend provides it."),
            ToolReturnSpec("signature", "str | null", "Declaration signature text."),
            ToolReturnSpec("value", "str | null", "Declaration value/body text."),
            ToolReturnSpec("full_declaration", "str | null", "Complete declaration text."),
            ToolReturnSpec("docstring", "str | null", "Declaration docstring text."),
            ToolReturnSpec(
                "decl_start_pos",
                "Position | null",
                "Declaration start position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "decl_end_pos",
                "Position | null",
                "Declaration end position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "doc_start_pos",
                "Position | null",
                "Docstring start position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
            ToolReturnSpec(
                "doc_end_pos",
                "Position | null",
                "Docstring end position.",
                children=(
                    ToolReturnSpec("line", "int", "Line number."),
                    ToolReturnSpec("column", "int", "Column number."),
                ),
            ),
        ),
    ),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="declarations",
        canonical_name="declarations.extract",
        raw_name="extract",
        api_path="/declarations/extract",
        description=(
            "Extract declarations from a single Lean file target."
        ),
        params=_EXTRACT_PARAMS,
        returns=_EXTRACT_RETURNS,
    ),
    GroupToolSpec(
        group_name="declarations",
        canonical_name="declarations.locate",
        raw_name="locate",
        api_path="/declarations/locate",
        description=(
            "Locate declaration target from a source file symbol and return matched declaration content."
        ),
        params=_LOCATE_PARAMS,
        returns=_LOCATE_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class DeclarationsGroupPlugin(GroupPlugin):
    group_name: str = "declarations"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.DECLARATIONS_BACKENDS, BackendKey.LSP_CLIENT_MANAGER)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_declarations_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_declarations_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "declarations.extract": lambda payload: handle_declarations_extract(service, payload),
            "declarations.locate": lambda payload: handle_declarations_locate(service, payload),
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
        extract_spec = _TOOL_SPEC_MAP["declarations.extract"]
        for alias in aliases_by_canonical.get("declarations.extract", ()):
            self._register_extract(
                mcp=mcp,
                alias=alias,
                spec=extract_spec,
                service=service,
                prune_none=prune_none,
            )
        locate_spec = _TOOL_SPEC_MAP["declarations.locate"]
        for alias in aliases_by_canonical.get("declarations.locate", ()):
            self._register_locate(
                mcp=mcp,
                alias=alias,
                spec=locate_spec,
                service=service,
                prune_none=prune_none,
            )

    @staticmethod
    def _register_extract(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        async def _declarations_extract(
            target: Annotated[
                str,
                Field(description=_param_desc(spec, "target")),
            ],
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "target": target,
            }
            return await run_sync_mcp_service_handler(
                handle_declarations_extract,
                service,
                prune_none(payload),
            )

    @staticmethod
    def _register_locate(
        *,
        mcp: Any,
        alias: str,
        spec: GroupToolSpec,
        service: Any,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description=spec.render_mcp_description(),
        )
        async def _declarations_locate(
            source_file: Annotated[
                str,
                Field(description=_param_desc(spec, "source_file")),
            ],
            symbol: Annotated[
                str,
                Field(description=_param_desc(spec, "symbol")),
            ],
            project_root: Annotated[
                str | None,
                Field(description=_param_desc(spec, "project_root")),
            ] = None,
            line: Annotated[
                int | None,
                Field(description=_param_desc(spec, "line")),
            ] = None,
            column: Annotated[
                int | None,
                Field(description=_param_desc(spec, "column")),
            ] = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "source_file": source_file,
                "symbol": symbol,
                "line": line,
                "column": column,
            }
            return await run_sync_mcp_service_handler(
                handle_declarations_locate,
                service,
                prune_none(payload),
            )


__all__ = ["DeclarationsGroupPlugin"]
