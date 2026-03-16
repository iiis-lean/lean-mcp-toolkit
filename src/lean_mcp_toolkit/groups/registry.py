"""Built-in group plugin registry."""

from __future__ import annotations

from .diagnostics.plugin import DiagnosticsGroupPlugin
from .plugin_base import GroupPlugin


def builtin_group_plugins() -> tuple[GroupPlugin, ...]:
    return (DiagnosticsGroupPlugin(),)


__all__ = ["builtin_group_plugins"]
