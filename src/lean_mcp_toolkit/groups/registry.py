"""Built-in group plugin registry."""

from __future__ import annotations

from .build_base.plugin import BuildBaseGroupPlugin
from .declarations.plugin import DeclarationsGroupPlugin
from .diagnostics.plugin import DiagnosticsGroupPlugin
from .lsp_assist.plugin import LspAssistGroupPlugin
from .lsp_heavy.plugin import LspHeavyGroupPlugin
from .lsp_core.plugin import LspCoreGroupPlugin
from .mathlib_nav.plugin import MathlibNavGroupPlugin
from .plugin_base import GroupPlugin
from .proof_search_alt.plugin import ProofSearchAltGroupPlugin
from .search_alt.plugin import SearchAltGroupPlugin
from .search_core.plugin import SearchCoreGroupPlugin
from .search_nav.plugin import SearchNavGroupPlugin


def builtin_group_plugins() -> tuple[GroupPlugin, ...]:
    return (
        BuildBaseGroupPlugin(),
        DiagnosticsGroupPlugin(),
        DeclarationsGroupPlugin(),
        LspCoreGroupPlugin(),
        LspAssistGroupPlugin(),
        LspHeavyGroupPlugin(),
        SearchAltGroupPlugin(),
        SearchCoreGroupPlugin(),
        MathlibNavGroupPlugin(),
        SearchNavGroupPlugin(),
        ProofSearchAltGroupPlugin(),
    )


__all__ = ["builtin_group_plugins"]
