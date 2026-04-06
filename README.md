# Lean MCP Toolkit

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Lean 4](https://img.shields.io/badge/lean-4-informational)
![MCP](https://img.shields.io/badge/MCP-supported-green)
![HTTP API](https://img.shields.io/badge/HTTP%20API-supported-green)
![CLI](https://img.shields.io/badge/CLI-supported-green)

`lean-mcp-toolkit` is a unified Lean tool server that exposes one configurable
tool catalog through MCP, HTTP API, remote CLI, and local shell entrypoints. It
combines LSP-based inspection tools, declaration/search utilities,
diagnostics/lint workflows, and lightweight source-analysis backends behind
shared contracts.

Quick links: [Usage](docs/usage/README.md) · [Tool Catalog](docs/tool_catalog/README.md) · [Architecture](docs/architecture/README.md) · [Configuration](docs/configuration/README.md)

## Overview

This project focuses on single-agent Lean tooling:

- Lean file inspection, proof-state queries, and widget access
- Declaration extraction, symbol location, and indexed declaration search
- Build, diagnostics, and lint checks such as `no_sorry` and `axiom_audit`
- Configurable backend selection for selected capabilities
- One shared tool catalog across MCP, HTTP API, remote CLI, and local shell

## Access Modes

`lean-mcp-toolkit` supports four access surfaces:

- **MCP server** for MCP-compatible clients
- **HTTP API** with JSON request/response contracts under `/api/v1`
- **Remote CLI** via `lean-cli-toolkit`, which reads the live tool catalog from a running server
- **Local interactive shell** via `lean-mcp-toolkit shell`

Visible tool names depend on the active server configuration (enabled groups,
tool naming mode, include/exclude filters). The remote CLI always reflects the
currently exposed aliases reported by the running server.

## Quick Start

Start a server:

```bash
lean-mcp-toolkit serve --config path/to/toolkit.yaml
```

Inspect the live tool catalog:

```bash
lean-cli-toolkit tools
```

Run a remote tool command:

```bash
lean-cli-toolkit diagnostics lint \
  --project-root /path/to/project \
  --targets MyProject/Package.lean
```

Start a local interactive shell:

```bash
lean-mcp-toolkit shell --config path/to/toolkit.yaml
```

For complete startup and CLI usage, see [docs/usage/README.md](docs/usage/README.md).

## Tool Groups

The toolkit is configured by tool groups internally, but end users typically
interact with canonical tool names or visible aliases.

| Group | Theme | Example tools |
|---|---|---|
| `diagnostics` | build, file diagnostics, lint checks | `diagnostics.build`, `diagnostics.lint`, `diagnostics.lint.no_sorry` |
| `declarations` | declaration extraction and symbol location | `declarations.extract`, `declarations.locate` |
| `lsp_core` / `lsp_assist` / `lsp_heavy` | Lean LSP inspection and proof-assist queries | `lsp.hover`, `lsp.goal`, `lsp.proof_profile` |
| `search_core` | LeanExplore-backed declaration search | `lean_explore.find`, `lean_explore.get` |
| `search_nav` | local repository navigation and lightweight source search | `repo_nav.tree`, `repo_nav.local_decl.find`, `repo_nav.grep` |
| `mathlib_nav` | mathlib tree/outline/read navigation | `mathlib_nav.tree`, `mathlib_nav.file_outline`, `mathlib_nav.grep` |
| `search_alt` | external search providers | `leansearch`, `leandex`, `loogle`, `leanfinder` |
| `proof_search_alt` | external proof-search providers | `proof_search_alt.state_search`, `proof_search_alt.hammer_premise` |
| `build_base` | direct workspace build entrypoint | `build.workspace` |

For the full tool-by-tool reference, backend notes, provenance, and upstream
name mapping, see [docs/tool_catalog/tool_reference.md](docs/tool_catalog/tool_reference.md).

## Documentation

- [Usage](docs/usage/README.md): server startup, HTTP access, remote CLI, and local shell
- [Tool Catalog](docs/tool_catalog/README.md): canonical tool inventory and navigation guide
- [Tool Reference](docs/tool_catalog/tool_reference.md): detailed tool tables, provenance, and backend notes
- [Architecture](docs/architecture/README.md): server/plugin/backend/interface structure
- [Configuration](docs/configuration/README.md): runtime configuration, backend selection, and naming controls

## Repository Layout

- `src/`: source code
- `tests/`: test suite
- `docs/`: public and reusable documentation
- `dev_docs/`: local development notes and design records
- `data/`: local data and generated artifacts
- `configs/`: configuration files and templates
