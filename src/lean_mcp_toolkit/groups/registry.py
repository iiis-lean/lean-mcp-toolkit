"""Built-in group plugin registry."""

from __future__ import annotations

from .declarations.plugin import DeclarationsGroupPlugin
from .diagnostics.plugin import DiagnosticsGroupPlugin
from .lsp_core.plugin import LspCoreGroupPlugin
from .plugin_base import GroupPlugin
from .search_core.plugin import SearchCoreGroupPlugin


def builtin_group_plugins() -> tuple[GroupPlugin, ...]:
    return (
        DiagnosticsGroupPlugin(),
        DeclarationsGroupPlugin(),
        LspCoreGroupPlugin(),
        SearchCoreGroupPlugin(),
    )


__all__ = ["builtin_group_plugins"]
