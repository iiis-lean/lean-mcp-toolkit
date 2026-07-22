<p align="center">
  <img
    src="assets/lean-mcp-toolkit-logo.png"
    alt="Lean MCP Toolkit logo"
    width="190"
  >
</p>

<h1 align="center">Lean MCP Toolkit</h1>

<p align="center">
  <strong>One configurable Lean tool catalog across MCP, HTTP, remote CLI, and local shell.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-172554?style=flat-square">
  </a>
  <img alt="Version 0.1.0" src="https://img.shields.io/badge/version-0.1.0-d97706?style=flat-square">
  <a href="https://lean-lang.org/">
    <img alt="Lean 4" src="https://img.shields.io/badge/Lean-4-6b4fbb?style=flat-square">
  </a>
  <a href="docs/usage/README.md#2-http-api">
    <img alt="MCP and HTTP" src="https://img.shields.io/badge/interfaces-MCP_%2B_HTTP-0f8f88?style=flat-square">
  </a>
  <a href="docs/tool_catalog/README.md">
    <img alt="Structured tool catalog" src="https://img.shields.io/badge/catalog-structured-2563eb?style=flat-square">
  </a>
  <a href="LICENSE">
    <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-e45132?style=flat-square">
  </a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a>
  &middot;
  <a href="docs/README.md">Documentation</a>
  &middot;
  <a href="docs/tool_catalog/README.md">Tool Catalog</a>
  &middot;
  <a href="docs/architecture/README.md">Architecture</a>
  &middot;
  <a href="docs/configuration/README.md">Configuration</a>
  &middot;
  <a href="https://github.com/iiis-lean/lean-constellation">Lean Constellation</a>
</p>

Lean MCP Toolkit is a unified Lean tool server for proof-engineering Agents,
interactive clients, and application runtimes. It combines Lean LSP
inspection, declaration analysis, source navigation, search, diagnostics,
linting, and build operations behind shared contracts and a configurable tool
catalog.

Each tool has one canonical specification and structured response shape. The
same active catalog can be exposed as MCP tools, HTTP JSON endpoints, a
remote-first CLI, or an in-process interactive shell.

<table>
  <tr>
    <td width="33%" valign="top">
      <strong>One Tool Catalog</strong><br><br>
      Enable groups, filter individual tools, select naming modes, and discover
      the exact live surface instead of maintaining separate client lists.
    </td>
    <td width="33%" valign="top">
      <strong>Shared Contracts</strong><br><br>
      MCP output schemas and HTTP JSON payloads are generated from the same
      structured toolkit response contracts.
    </td>
    <td width="33%" valign="top">
      <strong>Pluggable Backends</strong><br><br>
      Route selected capabilities through LSP, Lean, LeanInteract, text-based
      analysis, local or remote LeanExplore, and external search providers.
    </td>
  </tr>
</table>

## What It Provides

- **Lean inspection** — goals, term goals, hover information, outlines, code
  actions, completions, widgets, proof profiles, and snippet execution.
- **Declarations and navigation** — declaration extraction and location,
  repository and Mathlib trees, outlines, file windows, imports, scopes,
  references, and grep-style search.
- **Search** — local or remotely deployed LeanExplore, LeanSearch, LeanDex,
  Loogle, LeanFinder, arXiv theorem retrieval, state search, and premise
  suggestions.
- **Diagnostics and trust checks** — workspace builds, file/target diagnostics,
  `no_sorry`, direct axiom detection, axiom-usage probing, and configurable
  backend selection.
- **Consistent access** — MCP, HTTP API, remote CLI, and local shell all derive
  their visible commands and schemas from the active server configuration.
- **Operational backends** — reusable Lean command, LSP, LeanInteract,
  LeanExplore, external provider, and lightweight `text_ast` runtimes.

## How It Fits Together

```text
MCP client          HTTP client        lean-cli-toolkit       local shell
     │                   │                    │                    │
     └───────────────────┴──────────┬─────────┴────────────────────┘
                                    ▼
                           live tool catalog
                 canonical specs · aliases · output schemas
                                    │
                                    ▼
                              group plugins
       build · diagnostics · declarations · LSP · search · navigation
                                    │
                                    ▼
                         services and interfaces
                                    │
                                    ▼
 Lean/Lake · LSP · LeanInteract · text_ast · LeanExplore · search providers
```

The transport layer remains thin. Group plugins bind canonical tool specs to
transport-independent services and backend dependencies, while selected
capabilities use internal interfaces to switch implementations without
changing their public contracts.

`GET /api/v1/meta/tools` is the canonical discovery endpoint. The remote CLI
queries it at runtime and builds its command tree from the tools and aliases
actually exposed by the target server.

## Access Surfaces

| Surface | Entry point | Best suited for |
| --- | --- | --- |
| **MCP** | Toolkit MCP server | Agent runtimes and MCP-compatible clients |
| **HTTP API** | `/api/v1` JSON routes | Services, scripts, health checks, and language-agnostic integrations |
| **Remote CLI** | `lean-cli-toolkit` | Operators and shell automation against a running server |
| **Local shell** | `lean-mcp-toolkit shell` | Direct interactive use with the local service graph |

Visible aliases depend on enabled groups, naming mode, and include/exclude
filters. Public documentation uses canonical names; live MCP/HTTP/CLI surfaces
reflect the selected configuration.

## Quick Start

Lean MCP Toolkit requires Python 3.11 or newer. Install the server dependencies
from a source checkout:

```bash
python -m pip install -e '.[server]'
```

Start with the default configuration or an explicit YAML file:

```bash
lean-mcp-toolkit serve
lean-mcp-toolkit serve --config path/to/toolkit.yaml
```

Inspect the resolved configuration:

```bash
lean-mcp-toolkit print-config --config path/to/toolkit.yaml
```

Discover the live catalog and invoke a tool through the remote CLI:

```bash
lean-cli-toolkit tools

lean-cli-toolkit diagnostics lint \
  --project-root /path/to/project \
  --targets MyProject/Package.lean
```

Or call the shared HTTP surface directly:

```bash
curl http://127.0.0.1:18080/api/v1/meta/tools

curl -X POST http://127.0.0.1:18080/api/v1/diagnostics/lint \
  -H 'Content-Type: application/json' \
  -d '{
    "project_root": "/path/to/project",
    "targets": ["MyProject/Package.lean"]
  }'
```

For in-process interactive use:

```bash
lean-mcp-toolkit shell --config path/to/toolkit.yaml
```

Inside the shell, the same live command vocabulary is available without the
`lean-cli-toolkit` prefix.

## Tool Families

| Group | Theme | Representative canonical tools |
| --- | --- | --- |
| `build_base` | Direct workspace build | `build.workspace` |
| `diagnostics` | Build/file diagnostics and lint checks | `diagnostics.build`, `diagnostics.lint`, `diagnostics.lint.no_sorry` |
| `declarations` | Declaration extraction and symbol location | `declarations.extract`, `declarations.locate` |
| `lsp_core` | Core Lean LSP inspection | `lsp.goal`, `lsp.hover`, `lsp.file_outline`, `lsp.run_snippet` |
| `lsp_assist` | Higher-level proof assistance | `lsp.completions`, `lsp.multi_attempt`, `lsp.theorem_soundness` |
| `lsp_heavy` | Widget and proof-profile inspection | `lsp.widgets`, `lsp.widget_source`, `lsp.proof_profile` |
| `search_core` | LeanExplore declaration search | `lean_explore.find`, `lean_explore.get` |
| `search_nav` | Local repository navigation | `repo_nav.tree`, `repo_nav.local_decl.find`, `repo_nav.grep` |
| `mathlib_nav` | Mathlib navigation | `mathlib_nav.tree`, `mathlib_nav.read`, `mathlib_nav.grep` |
| `search_alt` | External search adapters | `leansearch`, `leandex`, `loogle`, `leanfinder` |
| `proof_search_alt` | External proof-search adapters | `proof_search_alt.state_search`, `proof_search_alt.hammer_premise` |

The [Tool Catalog](docs/tool_catalog/README.md) provides the navigation map.
The [Tool Reference](docs/tool_catalog/tool_reference.md) records detailed
contracts, provenance, upstream names, and backend notes.

## Configuration and Backends

Tool visibility is controlled by:

```text
groups.enabled_groups
groups.disabled_groups
groups.include_tools
groups.exclude_tools
groups.tool_naming_mode
```

Selected capabilities expose stable contracts over multiple implementations:

| Capability | Available backends | Default |
| --- | --- | --- |
| Declaration extraction | `text_ast`, `lean_interact`, `simple_lean` | `text_ast` |
| No-sorry checking | `text_ast`, `lean` | `text_ast` |
| Direct axiom declarations | `text_ast`, `lean` | `text_ast` |
| LeanExplore search | local runtime or remote HTTP service | configuration-dependent |

The axiom-usage probe remains Lean-backed even when direct declaration checks
use `text_ast`. Backend differences are explicit rather than hidden behind a
claim of identical implementation semantics.

See [Configuration](docs/configuration/README.md) for server settings, group
activation, backend fields, LSP runtime controls, startup warmup, and CLI
defaults.

## Remote LeanExplore

LeanExplore can run in the main Toolkit process or as a separately deployed
HTTP service while Agent-facing contracts remain `lean_explore.find` and
`lean_explore.get`.

Install the remote service dependencies:

```bash
python -m pip install -e '.[lean-explore-server]'
```

Start the service and point the main Toolkit at the example client config:

```bash
export LEANEXPLORE_API_KEY='replace-with-a-secret'

lean-mcp-toolkit-explore-server \
  --lean-version 4.32.0 \
  --host 127.0.0.1 \
  --port 18081

lean-mcp-toolkit serve \
  --config configs/lean_explore_remote_client.example.yaml
```

The remote adapter validates Lean-version metadata when configured to verify
on startup. See [Remote LeanExplore Service](docs/usage/README.md#5-remote-leanexplore-service)
for cache preparation, authentication, SSH forwarding, worker limits, and the
currently supported index mappings.

## Ecosystem

| Project | Relationship |
| --- | --- |
| **[Lean Constellation](https://github.com/iiis-lean/lean-constellation)** | Uses Toolkit HTTP/MCP capabilities and ToolViews for multi-repository Lean formalization workflows. |
| **[Agent Runtime Kit](https://github.com/xukp20/agent-runtime-kit)** | Provides the provider-neutral Agent and Flow/Step runtime underneath Lean Constellation; application tools remain owned by Toolkit/LC. |
| **[IIIS LEAN](https://github.com/iiis-lean)** | GitHub organization for the Lean formalization and tooling projects. |

Lean MCP Toolkit itself is Agent-agnostic: it exposes Lean capabilities but
does not schedule Agents, define application workflows, or own project-level
formalization policy.

## Documentation

| Area | Entry point |
| --- | --- |
| Documentation | [Public documentation index](docs/README.md) |
| Usage | [Server, HTTP, remote CLI, shell, and LeanExplore](docs/usage/README.md) |
| Tool catalog | [Group-level catalog](docs/tool_catalog/README.md) |
| Tool reference | [Detailed tools, provenance, and backends](docs/tool_catalog/tool_reference.md) |
| Architecture | [Server, plugin, service, backend, and interface layers](docs/architecture/README.md) |
| Configuration | [Runtime, groups, backends, and CLI defaults](docs/configuration/README.md) |

## Testing

With the development/test dependencies available, run the deterministic suite:

```bash
python -m pytest
```

Tests are organized around configuration, contracts, transports, application
entry points, backends, group plugins, and integration behavior.

## Development Status

Lean MCP Toolkit is under active development. Canonical tool contracts and
structured response shapes are the stable integration surface; visible aliases,
enabled groups, and backend availability remain deployment configuration.

<p align="center">
  <a href="https://github.com/iiis-lean"><strong>IIIS LEAN</strong></a>
</p>
