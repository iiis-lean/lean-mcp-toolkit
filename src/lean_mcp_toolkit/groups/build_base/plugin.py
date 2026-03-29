"""build_base group plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Mapping

try:
    from pydantic import Field
except Exception:  # pragma: no cover

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        _ = args, kwargs
        return None

from ...adapters.http import handle_build_workspace
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
from .factory import create_build_base_client, create_build_base_service

_WORKSPACE_PARAMS: tuple[ToolParamSpec, ...] = (
    ToolParamSpec(
        name="project_root",
        type_hint="str | null",
        required=False,
        default_value="server default project root",
        description="Lean project root directory. If not provided, server default root is used.",
    ),
    ToolParamSpec(
        name="targets",
        type_hint="list[str] | str | null",
        required=False,
        default_value="null (build entire workspace)",
        description=(
            "Optional Lean targets to build. Supports Lean dot path, relative .lean path, "
            "or absolute .lean path under project root."
        ),
    ),
    ToolParamSpec(
        name="target_facet",
        type_hint="str | null",
        required=False,
        default_value="null",
        description="Optional `lake build` target facet, for example `deps` or `leanArts`.",
    ),
    ToolParamSpec(
        name="timeout_seconds",
        type_hint="int | null",
        required=False,
        default_value="build_base.default_timeout_seconds",
        description="Command timeout in seconds.",
    ),
    ToolParamSpec(
        name="clean_first",
        type_hint="bool | null",
        required=False,
        default_value="build_base.default_clean_first",
        description="Whether to run `lake clean` before `lake build`.",
    ),
)

_WORKSPACE_RETURNS: tuple[ToolReturnSpec, ...] = (
    ToolReturnSpec("success", "bool", "Whether the final build command succeeded."),
    ToolReturnSpec("error_message", "str | null", "Failure summary when success=false."),
    ToolReturnSpec("project_root", "str", "Resolved project root."),
    ToolReturnSpec("targets", "list[str]", "Resolved module targets passed to lake build."),
    ToolReturnSpec("target_facet", "str | null", "Target facet used for build."),
    ToolReturnSpec("executed_commands", "list[list[str]]", "Executed command argv arrays."),
    ToolReturnSpec("returncode", "int", "Return code of the final executed command."),
    ToolReturnSpec("timed_out", "bool", "Whether the final command timed out."),
    ToolReturnSpec("stdout", "str", "Combined stdout from executed commands."),
    ToolReturnSpec("stderr", "str", "Combined stderr from executed commands."),
)

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="build_base",
        canonical_name="build.workspace",
        raw_name="workspace",
        api_path="/build/workspace",
        description="Run `lake build` for the whole workspace or selected Lean targets.",
        params=_WORKSPACE_PARAMS,
        returns=_WORKSPACE_RETURNS,
    ),
)

_TOOL_SPEC_MAP: dict[str, GroupToolSpec] = {spec.canonical_name: spec for spec in _TOOL_SPECS}


def _param_desc(spec: GroupToolSpec, name: str) -> str:
    for item in spec.params:
        if item.name == name:
            return item.description
    return ""


@dataclass(slots=True, frozen=True)
class BuildBaseGroupPlugin(GroupPlugin):
    group_name: str = "build_base"

    def backend_dependencies(self) -> tuple[str, ...]:
        return (BackendKey.LEAN_COMMAND_RUNTIME, BackendKey.LEAN_TARGET_RESOLVER)

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ):
        return create_build_base_service(config=config, backends=backends)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_build_base_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {"build.workspace": lambda payload: handle_build_workspace(service, payload)}

    def register_mcp_tools(
        self,
        mcp: Any,
        *,
        service: Any,
        aliases_by_canonical: Mapping[str, tuple[str, ...]],
        normalize_str_list,
        prune_none,
    ) -> None:
        spec = _TOOL_SPEC_MAP["build.workspace"]
        for alias in aliases_by_canonical.get("build.workspace", ()):
            @mcp.tool(name=alias, description=spec.render_mcp_description())
            async def _build_workspace(
                project_root: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "project_root")),
                ] = None,
                targets: Annotated[
                    list[str] | str | None,
                    Field(description=_param_desc(spec, "targets")),
                ] = None,
                target_facet: Annotated[
                    str | None,
                    Field(description=_param_desc(spec, "target_facet")),
                ] = None,
                timeout_seconds: Annotated[
                    int | None,
                    Field(description=_param_desc(spec, "timeout_seconds")),
                ] = None,
                clean_first: Annotated[
                    bool | None,
                    Field(description=_param_desc(spec, "clean_first")),
                ] = None,
            ) -> JsonDict:
                payload = prune_none(
                    {
                        "project_root": project_root,
                        "targets": normalize_str_list(targets),
                        "target_facet": target_facet,
                        "timeout_seconds": timeout_seconds,
                        "clean_first": clean_first,
                    }
                )
                return await run_sync_mcp_service_handler(
                    handle_build_workspace,
                    service,
                    payload,
                )
