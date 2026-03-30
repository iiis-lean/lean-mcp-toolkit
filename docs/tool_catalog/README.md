# Tool Catalog

This section documents the tool surface exposed by `lean-mcp-toolkit`.

## How to Read This Catalog

- The tables in this directory use **canonical tool names**.
- Actual visible aliases in MCP, HTTP, and CLI may vary with server config.
- Group membership is documented to explain organization and activation, not to
  define the only valid user-facing names.

## Tool Families

| Group | Theme | Representative tools |
|---|---|---|
| `build_base` | direct workspace build entrypoint | `build.workspace` |
| `diagnostics` | build/file diagnostics and lint checks | `diagnostics.build`, `diagnostics.lint`, `diagnostics.lint.no_sorry` |
| `declarations` | declaration extraction and symbol location | `declarations.extract`, `declarations.locate` |
| `lsp_core` | core Lean LSP inspection | `lsp.hover`, `lsp.goal`, `lsp.file_outline` |
| `lsp_assist` | higher-level LSP proof assistance | `lsp.completions`, `lsp.multi_attempt`, `lsp.theorem_soundness` |
| `lsp_heavy` | heavier widget/profile inspection | `lsp.widgets`, `lsp.widget_source`, `lsp.proof_profile` |
| `search_core` | LeanExplore-backed declaration search | `search.mathlib_decl.find`, `search.mathlib_decl.get` |
| `mathlib_nav` | mathlib tree/outline/read navigation | `search.mathlib_nav.tree`, `search.mathlib_nav.file_outline`, `search.mathlib_nav.read` |
| `search_nav` | local repository navigation and lightweight source search | `search.repo_nav.tree`, `search.local_decl.find`, `search.local_refs.find` |
| `search_alt` | external search providers | `search_alt.leansearch`, `search_alt.leandex`, `search_alt.loogle`, `search_alt.leanfinder` |
| `proof_search_alt` | external proof-search providers | `proof_search_alt.state_search`, `proof_search_alt.hammer_premise` |

## Detailed Reference

For the detailed per-tool reference, including provenance, upstream names, and
backend notes, see:

- [tool_reference.md](tool_reference.md)

