# Tool Reference

This document provides a detailed reference for the canonical tools exposed by
`lean-mcp-toolkit`, including provenance and backend notes where applicable.

## Provenance Conventions

The `Source` and `Original name / upstream reference` columns follow these rules:

- **Adapted upstream tool**: both `Source` and upstream/original tool name are listed.
- **Local implementation using a library/runtime**: the runtime or package is
  listed in `Source`, and `Original name` is left blank.
- **Local implementation**: `Source` is listed as `Local implementation`.

## Build and Diagnostics

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `build.workspace` | Run `lake build` for a workspace or selected targets. | Local implementation |  | Uses the Lean command runtime. |
| `diagnostics.build` | Collect Lean diagnostics for a target set, optionally building deps/artifacts. | Local implementation |  | Uses Lean command diagnostics and `lake build`. |
| `diagnostics.file` | Collect diagnostics for a single Lean file. | Local implementation |  | Uses Lean command diagnostics. |
| `diagnostics.lint` | Run the configured lint checks over one or more targets. | Local implementation |  | Dispatches to `no_sorry` and `axiom_audit`. |
| `diagnostics.lint.no_sorry` | Detect `sorry`/`admit` placeholders. | Local implementation |  | Supports `text_ast` and Lean-based backends. |
| `diagnostics.lint.axiom_audit` | Check direct axiom declarations and probe theorem dependencies. | Local implementation |  | Direct declaration checks can use `text_ast` or Lean-based backends; usage probing remains Lean-based. |

### Diagnostics Backend Roles

| Tool / sub-capability | Backend | Default | Source | Original name / upstream reference | Notes |
|---|---|---|---|---|---|
| `diagnostics.lint.no_sorry` source scan | `text_ast` | Yes | Local implementation informed by `lean4-skills` style source scanning |  | Fast text-level scan; ignores comments and strings. |
| `diagnostics.lint.no_sorry` semantic diagnostics path | `lean` | No | Local implementation |  | Uses Lean command diagnostics and source snippets. |
| `diagnostics.lint.axiom_audit` direct declaration check | `text_ast` | Yes | Local implementation with toolkit `text_ast` backend |  | Covers direct `axiom` / `constant` / alias-style source checks. |
| `diagnostics.lint.axiom_audit` direct declaration check | `lean` | No | Local implementation |  | Lean-backed declaration scan. |
| `diagnostics.lint.axiom_audit` usage probe | Lean probe | Yes | Local implementation |  | Uses the existing probe-file / `#print axioms` route. |

## Declarations

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `declarations.extract` | Extract top-level declarations from a Lean source target. | Local implementation |  | Supports multiple declaration backends. |
| `declarations.locate` | Locate a symbol through source position + declaration extraction. | Local implementation |  | Uses LSP location plus declaration extraction. |

### Declaration Extraction Backends

| Capability | Backend | Default | Source | Original name / upstream reference | Notes |
|---|---|---|---|---|---|
| `declarations.extract` | `text_ast` | Yes | Local implementation, informed by LongCat-Flash-Prover design ideas |  | Fast text/AST extraction; source-oriented. |
| `declarations.extract` | `lean_interact` | No | LeanInteract runtime |  | Uses LeanInteract-backed extraction. |
| `declarations.extract` | `simple_lean` | No | Local implementation |  | Lightweight Lean-oriented compatibility backend. |

## LSP Tools

### Core LSP tools

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `lsp.file_outline` | Return imports and declaration outline for a file. | `lean-lsp-mcp` / upstream | `lean_file_outline` | LSP client based. |
| `lsp.goal` | Return proof goals at a line/column or before/after a line. | `lean-lsp-mcp` / upstream | `lean_goal` | LSP client based. |
| `lsp.term_goal` | Return expected type / term goal at a position. | `lean-lsp-mcp` / upstream | `lean_term_goal` | LSP client based. |
| `lsp.hover` | Return hover/type/doc information at a position. | `lean-lsp-mcp` / upstream | `lean_hover_info` | LSP client based. |
| `lsp.code_actions` | Return code actions / resolved edits at a line. | `lean-lsp-mcp` / upstream | `lean_code_actions` | LSP client based. |

### Assistive LSP tools

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `lsp.completions` | Return IDE completions at a position. | `lean-lsp-mcp` / upstream | `lean_completions` | LSP client based. |
| `lsp.declaration_file` | Locate the declaration file for a symbol. | `lean-lsp-mcp` / upstream | `lean_declaration_file` | LSP client based. |
| `lsp.multi_attempt` | Try multiple tactic snippets against one goal. | `lean-lsp-mcp` / upstream | `lean_multi_attempt` | LSP client based. |
| `lsp.run_snippet` | Run a self-contained Lean snippet and report diagnostics. | Local implementation inspired by LSP tool workflows |  | Uses command/runtime execution rather than a migrated MCP tool. |
| `lsp.theorem_soundness` | Inspect theorem verification / soundness-oriented checks. | Local implementation |  | Toolkit-owned higher-level LSP-assisted tool. |

### Heavy LSP tools

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `lsp.widgets` | Return widget payloads at a source position. | `lean-lsp-mcp` / upstream | `lean_get_widgets` | LSP client based. |
| `lsp.widget_source` | Return the JavaScript source of a widget by hash. | `lean-lsp-mcp` / upstream | `lean_get_widget_source` | LSP client based. |
| `lsp.proof_profile` | Profile theorem checking / proof elaboration lines. | Local implementation |  | Uses Lean command profile flow. |

## LeanExplore-backed Search

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `search.mathlib_decl.find` | Search indexed declarations by name or meaning. | `lean-explore` | search endpoint in `lean-explore` | Supports local and remote LeanExplore backends. |
| `search.mathlib_decl.get` | Fetch one indexed declaration by id. | `lean-explore` | get-by-id endpoint in `lean-explore` | Supports local and remote LeanExplore backends. |

## Repository and Mathlib Navigation

### Mathlib navigation

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `search.mathlib_nav.tree` | Browse the mathlib/module tree. | Local implementation |  | Source-navigation utility. |
| `search.mathlib_nav.file_outline` | Read a structured file outline for a mathlib file/module. | Local implementation |  | Source-navigation utility. |
| `search.mathlib_nav.read` | Read a file window with optional line numbers. | Local implementation |  | Source-navigation utility. |

### Local repository navigation

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `search.repo_nav.tree` | Browse the project repository tree. | Local implementation |  | Source-navigation utility. |
| `search.repo_nav.file_outline` | Return a structured outline for a local Lean file. | Local implementation |  | Source-navigation utility. |
| `search.repo_nav.read` | Read a local Lean file window. | Local implementation |  | Source-navigation utility. |
| `search.local_decl.find` | Find declarations in local Lean source trees. | Local implementation |  | Lightweight source search. |
| `search.local_import.find` | Find import relationships around a module query. | Local implementation |  | Lightweight source search. |
| `search.local_scope.find` | Find namespace/section/open/export scope commands. | Local implementation |  | Lightweight source search. |
| `search.local_text.find` | Search text inside structured Lean source scopes. | Local implementation |  | Lightweight source search. |
| `search.local_refs.find` | Find lightweight source references for a symbol. | Local implementation |  | Lightweight source search. |

## External Search Providers

| Canonical tool | Summary | Source | Original name / upstream reference | Backend notes |
|---|---|---|---|---|
| `search_alt.leansearch` | Query LeanSearch. | LeanSearch provider |  | External provider adapter. |
| `search_alt.leandex` | Query LeanDex. | LeanDex provider |  | External provider adapter. |
| `search_alt.loogle` | Query Loogle. | Loogle provider |  | External provider adapter. |
| `search_alt.leanfinder` | Query LeanFinder. | LeanFinder provider |  | External provider adapter. |
| `proof_search_alt.state_search` | Query state-search style theorem suggestions. | External proof-search provider |  | Uses LSP goal text plus provider call. |
| `proof_search_alt.hammer_premise` | Query hammer/premise suggestions. | External proof-search provider |  | Uses LSP goal text plus provider call. |

## Notes on Backends and Naming

- The canonical tool names above are stable documentation identifiers.
- MCP-visible aliases and CLI command paths depend on naming mode and enabled groups.
- Selected capabilities support multiple backends; see [../configuration/README.md](../configuration/README.md) for the relevant configuration fields.
- `text_ast` is a toolkit-owned lightweight backend informed by LongCat-Flash-Prover design ideas, but it is not a direct code import of that project.

