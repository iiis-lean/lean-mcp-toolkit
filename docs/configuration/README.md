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

## 5. Startup Warmup And Local LeanExplore Shutdown

The default startup warmup includes a `lean_explore.find` request with
`rerank_top=50`. For the local LeanExplore backend, this intentionally warms both
the embedding model and the cross-encoder reranker. Cold startup can take tens of
seconds on a GPU machine, but subsequent reranked Mathlib searches should avoid
the first-call model-load penalty.

For CUDA-backed local LeanExplore deployments, prefer one long-lived toolkit
server process shared by clients. Starting several independent local LeanExplore
processes can load duplicate embedding/reranker models and exhaust GPU memory.

On shutdown, the local LeanExplore backend disposes the async database engine,
drops references to embedding/reranker model objects, clears cached search
indices, and asks PyTorch to release CUDA cache. After stopping a GPU-backed
server, `nvidia-smi` and `lsof /dev/nvidia*` should not show a lingering toolkit
Python process.

If the same server also runs tools that fork Lean/LSP subprocesses after
HuggingFace tokenizers have been used, setting `TOKENIZERS_PARALLELISM=false` in
the server environment suppresses tokenizer fork warnings.

### Remote LeanExplore backend

`search_core.mathlib_lean_version` remains the single expected Lean/Mathlib
version for both local and remote operation. The default remains `4.28.0`.
Supported local index mappings currently include:

- `4.28.0` -> `20260217_050001`
- `4.32.0` -> `20260714_172516`

Remote operation is additive and does not change the `lean_explore.find` or
`lean_explore.get` tool contracts:

```yaml
search_core:
  mathlib_lean_version: "4.32.0"

backends:
  lean_explore:
    mode: api
    api_base_url: http://127.0.0.1:18081/api/v2
    api_key_env: LEANEXPLORE_API_KEY
    api_timeout_seconds: 120
    api_verify_on_startup: true
    api_health_path: /health
    api_trust_env: false
    api_verify_ssl: true
    api_retry_count: 2
    api_retry_backoff_seconds: 0.5
```

When `api_verify_on_startup` is enabled, the first backend activation checks the
remote health metadata and rejects a service whose `lean_version` differs from
`search_core.mathlib_lean_version`. Enable the normal Toolkit startup warmup to
make this check part of server startup rather than the first user request.

`api_trust_env=false` prevents inherited `HTTP_PROXY`, `HTTPS_PROXY`, and
`ALL_PROXY` settings from intercepting a loopback SSH tunnel. Keep
`api_verify_ssl=true` for HTTPS deployments.

See [the complete example config](../../configs/lean_explore_remote_client.example.yaml).

## 6. `lsp.run_snippet` Runtime Controls

The toolkit-owned `lsp.run_snippet` tool is configured under `lsp_core`:

- `lsp_core.run_snippet_default_timeout_seconds`
- `lsp_core.run_snippet_max_timeout_seconds`
- `lsp_core.run_snippet_max_code_chars`

These settings control the default snippet timeout, the hard upper bound for a
user-supplied timeout, and the maximum snippet size accepted by the server.

`run_snippet` also applies a toolkit-side hard timeout around diagnostics
collection so that cleanup and client recycle still happen if the underlying LSP
call does not return promptly.

## 7. Structured Output Notes

MCP tools now expose structured output schemas derived from the same toolkit
response contracts used by the HTTP API.

Practical implications:

- MCP clients that consume tool `outputSchema` can type structured results more precisely.
- HTTP routes keep returning plain JSON payloads with the same field layout.
- Core `lsp_core` inspection tools now return structured responses only; there is no
  `response_format=markdown` switch in the runtime config or request payloads.

## 8. CLI Defaults

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

## 9. Suggested Reading Order

For practical use:

1. Start with [../usage/README.md](../usage/README.md)
2. Then read [../tool_catalog/README.md](../tool_catalog/README.md)
3. Use [tool_reference.md](../tool_catalog/tool_reference.md) when selecting tool/backend combinations
