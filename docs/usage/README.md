# Usage

This document describes how to start `lean-mcp-toolkit`, inspect the live tool
catalog, and invoke tools through HTTP and CLI surfaces.

## 1. Start the Server

The server entrypoint remains `lean-mcp-toolkit`.

### Start with default configuration

```bash
lean-mcp-toolkit serve
```

### Start with an explicit configuration file

```bash
lean-mcp-toolkit serve --config path/to/toolkit.yaml
```

### Print the resolved configuration

```bash
lean-mcp-toolkit print-config --config path/to/toolkit.yaml
```

The same CLI also accepts the existing configuration override flags, such as:

```bash
lean-mcp-toolkit serve \
  --config path/to/toolkit.yaml \
  --project-root /path/to/project \
  --enable-group diagnostics \
  --enable-group declarations
```

## 2. HTTP API

By default the HTTP API is mounted under:

```text
/api/v1
```

The most useful discovery endpoint is:

```text
GET /api/v1/meta/tools
```

It returns the active tool catalog, including:

- canonical tool names
- visible aliases
- API paths
- parameter metadata
- return-field metadata

Example:

```bash
curl http://127.0.0.1:18080/api/v1/meta/tools
```

Tool invocations are JSON `POST` calls under the same prefix, for example:

```bash
curl -X POST http://127.0.0.1:18080/api/v1/diagnostics/lint \
  -H 'Content-Type: application/json' \
  -d '{
    "project_root": "/path/to/project",
    "targets": ["MyProject/Package.lean"]
  }'
```

## 3. Remote CLI: `lean-cli-toolkit`

`lean-cli-toolkit` is the remote-first command-line client. It does not embed
tool definitions statically; instead, it queries the running server for the
currently visible tool catalog and builds command help dynamically.

### Default base URL

If no base URL is provided, the CLI uses:

```text
http://127.0.0.1:18080
```

The base URL can be overridden by:

1. `--base-url`
2. `LEAN_CLI_TOOLKIT_BASE_URL`
3. the user config file

### List tools

```bash
lean-cli-toolkit tools
```

### Show tool help

```bash
lean-cli-toolkit diagnostics lint --help
lean-cli-toolkit lsp hover --help
```

### Call a tool

```bash
lean-cli-toolkit diagnostics lint \
  --project-root /path/to/project \
  --targets MyProject/Package.lean
```

### Pass payloads directly

Standard `--param-name` arguments are the primary interface. Two fallback
payload forms are also supported:

```bash
lean-cli-toolkit diagnostics lint --payload-file req.json
lean-cli-toolkit diagnostics lint --json '{"project_root": "...", "targets": ["Foo"]}'
```

### User config

The remote CLI stores per-user defaults in:

```text
~/.config/lean-cli-toolkit/config.toml
```

Examples:

```bash
lean-cli-toolkit config show
lean-cli-toolkit config set default-base-url http://127.0.0.1:18080
lean-cli-toolkit config set default-timeout-seconds 180
```

## 4. Local Interactive Shell

`lean-mcp-toolkit shell` starts a local interactive shell in the current
process. This mode constructs the same toolkit service graph as the server but
invokes tools directly rather than going through HTTP.

```bash
lean-mcp-toolkit shell --config path/to/toolkit.yaml
```

Inside the shell, use the same command syntax as the remote CLI, without the
`lean-cli-toolkit` prefix:

```text
tools
diagnostics lint --project-root /path/to/project --targets MyProject/Package.lean
lsp hover --project-root /path/to/project --file-path MyProject/Basic.lean --line 10 --column 5
```

Built-in shell commands:

- `tools`
- `help`
- `quit`
- `exit`

## 5. Tool Names and Aliases

The CLI command tree is generated from the live tool aliases exposed by the
running server. This means:

- visible commands depend on enabled groups and include/exclude filters
- alias spelling depends on tool naming mode
- canonical names are stable for documentation, but CLI-visible names may vary

The reference documentation uses canonical tool names. The remote CLI always
reflects the actual aliases exposed by the target server.

