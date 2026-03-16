"""MCP tool-adapter shims for diagnostics contracts.

This module exposes pure-python handlers so tool registration
can be wired later without changing request/response contracts.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...contracts.base import JsonDict
from ...core.services import DiagnosticsService
from ...groups.diagnostics.plugin import DiagnosticsGroupPlugin
from ..http import (
    handle_diagnostics_build,
    handle_diagnostics_lint,
    handle_diagnostics_lint_no_sorry,
)


@dataclass(slots=True, frozen=True)
class MCPToolSpec:
    name: str
    description: str


def _build_tool_specs() -> tuple[MCPToolSpec, ...]:
    plugin = DiagnosticsGroupPlugin()
    return tuple(
        MCPToolSpec(
            name=item.canonical_name,
            description=item.render_mcp_description(),
        )
        for item in plugin.tool_specs()
    )


DIAGNOSTICS_TOOL_SPECS: tuple[MCPToolSpec, ...] = _build_tool_specs()



def dispatch_tool(service: DiagnosticsService, tool_name: str, payload: JsonDict) -> JsonDict:
    if tool_name == "diagnostics.build":
        return handle_diagnostics_build(service, payload)
    if tool_name == "diagnostics.lint":
        return handle_diagnostics_lint(service, payload)
    if tool_name == "diagnostics.lint.no_sorry":
        return handle_diagnostics_lint_no_sorry(service, payload)
    raise KeyError(f"unsupported tool: {tool_name}")
