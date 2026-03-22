"""Canonical backend dependency keys."""

from __future__ import annotations


class BackendKey:
    """Stable identifiers used by group plugins to declare backend dependencies."""

    LEAN_COMMAND_RUNTIME = "lean.command_runtime"
    LEAN_TARGET_RESOLVER = "lean.path.target_resolver"
    DECLARATIONS_BACKENDS = "declarations.backends"
    LSP_CLIENT_MANAGER = "lsp.client_manager"
    LEAN_EXPLORE_BACKEND = "search.lean_explore.backend"


__all__ = ["BackendKey"]
