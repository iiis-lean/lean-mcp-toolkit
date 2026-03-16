"""MCP adapter package."""

from .diagnostics_tools import DIAGNOSTICS_TOOL_SPECS, MCPToolSpec, dispatch_tool

__all__ = ["MCPToolSpec", "DIAGNOSTICS_TOOL_SPECS", "dispatch_tool"]
