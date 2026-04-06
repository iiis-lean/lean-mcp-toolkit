# Configuration

This document summarizes the most important runtime configuration knobs for
`lean-mcp-toolkit`.

## 1. Server Configuration

Typical server-level settings include:

- `server.mode`
- `server.host`
- `server.port`
- `server.api_prefix`
- `server.default_project_root`
- MCP transport-related options

These settings control where the server runs and which transport surfaces are
enabled.

## 2. Group Activation

Tool visibility is controlled by group activation settings:

- `groups.enabled_groups`
- `groups.disabled_groups`
- `groups.include_tools`
- `groups.exclude_tools`
- `groups.tool_naming_mode`

This affects:

- MCP-visible aliases
- HTTP `/meta/tools`
- remote CLI command tree
- local shell command tree

## 3. Backend Selection

Selected capabilities support more than one backend implementation.

### Declaration extraction

Configuration field:

```text
declarations.default_backend
```

Supported values:

- `text_ast`
- `lean_interact`
- `simple_lean`

Default:

```text
text_ast
```

### No-sorry checks

Configuration field:

```text
diagnostics.no_sorry_backend
```

Supported values:

- `text_ast`
- `lean`

Default:

```text
text_ast
```

### Direct axiom declaration checks

Configuration field:

```text
diagnostics.axiom_declaration_backend
```

Supported values:

- `text_ast`
- `lean`

Default:

```text
text_ast
```

### Axiom usage checks

There is currently no alternate backend switch for the usage-probe stage of
`diagnostics.lint.axiom_audit`. That part remains on the Lean probe route.

## 4. Search and Backend Families

Several search-oriented capabilities are backed by configurable provider or
backend layers, including:

- LeanExplore backends
- search-provider adapters
- LSP runtime configuration
- LeanInteract runtime configuration

These are configured under the corresponding sections in the toolkit config.

## 5. `lsp.run_snippet` Runtime Controls

The toolkit-owned `lsp.run_snippet` tool is configured under `lsp_core`:

- `lsp_core.run_snippet_default_timeout_seconds`
- `lsp_core.run_snippet_max_timeout_seconds`
- `lsp_core.run_snippet_max_code_chars`

These settings control the default snippet timeout, the hard upper bound for a
user-supplied timeout, and the maximum snippet size accepted by the server.

`run_snippet` also applies a toolkit-side hard timeout around diagnostics
collection so that cleanup and client recycle still happen if the underlying LSP
call does not return promptly.

## 6. CLI Defaults

The remote CLI (`lean-cli-toolkit`) also has a user-scoped config file:

```text
~/.config/lean-cli-toolkit/config.toml
```

This stores client-side defaults such as:

- default base URL
- default API prefix
- default output format
- default timeout

These defaults are separate from the toolkit server configuration.

## 7. Suggested Reading Order

For practical use:

1. Start with [../usage/README.md](../usage/README.md)
2. Then read [../tool_catalog/README.md](../tool_catalog/README.md)
3. Use [tool_reference.md](../tool_catalog/tool_reference.md) when selecting tool/backend combinations
