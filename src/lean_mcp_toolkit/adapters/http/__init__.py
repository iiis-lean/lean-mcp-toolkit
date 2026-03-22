"""HTTP adapter package."""

from .declarations_routes import handle_declarations_extract, handle_declarations_locate
from .diagnostics_routes import (
    handle_diagnostics_build,
    handle_diagnostics_lint,
    handle_diagnostics_lint_axiom_audit,
    handle_diagnostics_lint_no_sorry,
)
from .lsp_core_routes import (
    handle_lsp_code_actions,
    handle_lsp_file_outline,
    handle_lsp_goal,
    handle_lsp_hover,
    handle_lsp_term_goal,
)
from .search_core_routes import (
    handle_search_local_decl_search,
    handle_search_mathlib_decl_get,
    handle_search_mathlib_decl_search,
)

__all__ = [
    "handle_declarations_extract",
    "handle_declarations_locate",
    "handle_diagnostics_build",
    "handle_diagnostics_lint",
    "handle_diagnostics_lint_axiom_audit",
    "handle_diagnostics_lint_no_sorry",
    "handle_lsp_file_outline",
    "handle_lsp_goal",
    "handle_lsp_term_goal",
    "handle_lsp_hover",
    "handle_lsp_code_actions",
    "handle_search_mathlib_decl_search",
    "handle_search_mathlib_decl_get",
    "handle_search_local_decl_search",
]
