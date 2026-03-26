"""Canonical backend dependency keys."""

from __future__ import annotations


class BackendKey:
    """Stable identifiers used by group plugins to declare backend dependencies."""

    LEAN_COMMAND_RUNTIME = "lean.command_runtime"
    LEAN_TARGET_RESOLVER = "lean.path.target_resolver"
    DECLARATIONS_BACKENDS = "declarations.backends"
    LSP_CLIENT_MANAGER = "lsp.client_manager"
    LEAN_EXPLORE_BACKEND = "search.lean_explore.backend"
    SEARCH_ALT_MANAGER = "search.providers.search_alt_manager"
    PROOF_SEARCH_ALT_MANAGER = "search.providers.proof_search_alt_manager"


__all__ = ["BackendKey"]
