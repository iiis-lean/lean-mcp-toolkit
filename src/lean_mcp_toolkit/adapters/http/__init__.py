"""HTTP adapter package."""

from .declarations_routes import handle_declarations_extract, handle_declarations_locate
from .diagnostics_routes import (
    handle_diagnostics_build,
    handle_diagnostics_file,
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
from .lsp_assist_routes import (
    handle_lsp_completions,
    handle_lsp_declaration_file,
    handle_lsp_multi_attempt,
    handle_lsp_run_snippet,
    handle_lsp_theorem_soundness,
)
from .mathlib_nav_routes import (
    handle_search_mathlib_nav_file_outline,
    handle_search_mathlib_nav_read,
    handle_search_mathlib_nav_tree,
)
from .search_core_routes import (
    handle_search_mathlib_decl_find,
    handle_search_mathlib_decl_get,
)
from .search_nav_routes import (
    handle_search_local_decl_find,
    handle_search_local_import_find,
    handle_search_local_refs_find,
    handle_search_local_scope_find,
    handle_search_local_text_find,
    handle_search_repo_nav_file_outline,
    handle_search_repo_nav_read,
    handle_search_repo_nav_tree,
)

__all__ = [
    "handle_declarations_extract",
    "handle_declarations_locate",
    "handle_diagnostics_build",
    "handle_diagnostics_file",
    "handle_diagnostics_lint",
    "handle_diagnostics_lint_axiom_audit",
    "handle_diagnostics_lint_no_sorry",
    "handle_lsp_file_outline",
    "handle_lsp_goal",
    "handle_lsp_term_goal",
    "handle_lsp_hover",
    "handle_lsp_code_actions",
    "handle_lsp_completions",
    "handle_lsp_declaration_file",
    "handle_lsp_multi_attempt",
    "handle_lsp_run_snippet",
    "handle_lsp_theorem_soundness",
    "handle_search_mathlib_decl_find",
    "handle_search_mathlib_decl_get",
    "handle_search_mathlib_nav_tree",
    "handle_search_mathlib_nav_file_outline",
    "handle_search_mathlib_nav_read",
    "handle_search_repo_nav_tree",
    "handle_search_repo_nav_file_outline",
    "handle_search_repo_nav_read",
    "handle_search_local_decl_find",
    "handle_search_local_import_find",
    "handle_search_local_scope_find",
    "handle_search_local_text_find",
    "handle_search_local_refs_find",
]
