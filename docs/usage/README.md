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
- machine-readable `output_schema` for structured MCP/HTTP result payloads

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

### Debug backend recycle endpoints

For runtime recovery and backend cleanup, the HTTP API also exposes debug-only
recycle endpoints:

```text
POST /api/v1/debug/backends/recycle/lsp
POST /api/v1/debug/backends/recycle/lean_interact
```

Each endpoint accepts an optional JSON body:

```json
{
  "project_root": "/path/to/project"
}
```

If `project_root` is omitted, the server default project root is used.

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

## 5. Remote LeanExplore Service

LeanExplore can run as a separate HTTP service while the main Toolkit process
continues to host local LSP, diagnostics, declaration, and repository tools.
The Agent-facing tools remain `lean_explore.find` and `lean_explore.get`.

Install the service dependencies on the GPU host:

```bash
pip install 'lean-mcp-toolkit[lean-explore-server]'
```

Start a service for the existing Lean 4.28.0 index:

```bash
export LEANEXPLORE_API_KEY='replace-with-a-secret'
TOKENIZERS_PARALLELISM=false \
lean-mcp-toolkit-explore-server \
  --lean-version 4.28.0 \
  --host 127.0.0.1 \
  --port 18081
```

For the supported Lean 4.32.0 index, fetch index `20260714_172516` into a
separate cache root so the older active index is not changed:

```bash
export LEAN_EXPLORE_CACHE_DIR=/srv/lean-explore-4.32/cache
lean-explore data fetch --version 20260714_172516

lean-mcp-toolkit-explore-server \
  --lean-version 4.32.0 \
  --cache-dir /srv/lean-explore-4.32/cache \
  --host 127.0.0.1 \
  --port 18081
```

The service exposes:

```text
GET /health
GET /api/v2/health
GET /api/v2/search
GET /api/v2/declarations/{declaration_id}
```

Search and declaration routes require the bearer token from
`LEANEXPLORE_API_KEY`. The health response includes `index_id`, `lean_version`,
and the detected Mathlib revision when available.

If the GPU host is reachable over SSH, forward its loopback service to the
Toolkit host:

```bash
ssh -NT \
  -L 127.0.0.1:18081:127.0.0.1:18081 \
  gpu-user@gpu-host
```

Then start the main Toolkit with the remote client configuration:

```bash
export LEANEXPLORE_API_KEY='the-same-secret'
lean-mcp-toolkit serve \
  --config configs/lean_explore_remote_client.example.yaml
```

Run only one service worker per GPU unless model sharing is provided outside the
process. Multiple workers load duplicate embedding and reranker models.

## 6. Tool Names and Aliases

The CLI command tree is generated from the live tool aliases exposed by the
running server. This means:

- visible commands depend on enabled groups and include/exclude filters
- alias spelling depends on tool naming mode
- canonical names are stable for documentation, but CLI-visible names may vary

The reference documentation uses canonical tool names. The remote CLI always
reflects the actual aliases exposed by the target server.
