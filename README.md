# lean-mcp-toolkit

A unified Lean MCP toolkit that aggregates diagnostics, search, and quality-check tools behind one configurable server, with shared schemas for both MCP and HTTP API access.

## Goals

- Provide a single MCP server with grouped, composable Lean tools.
- Keep workflow-control tools out of this repository; focus on single-agent independent tools.
- Support the same request/response schemas for both MCP and HTTP API surfaces.
- Allow startup-time selection of tool groups and individual tools.

## Planned Tool Sources

- lean-lsp-mcp-upstream
- lean-explore
- local aggregate tools (`compile_check`, `linter_check`)

## Planned Naming

Tool names are planned in dotted form:

- `quality.compile_check`
- `quality.linter_check`
- `lsp.diagnostic_messages`
- `search.search_summary`

## Repository Layout

- `src/`: source code
- `tests/`: tests
- `docs/`: reusable public docs (English)
- `dev_docs/`: local development docs (Chinese)
- `data/`: local data and artifacts (ignored)
- `configs/`: local config and templates
