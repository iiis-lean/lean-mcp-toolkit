# Architecture

This document describes the implementation structure of `lean-mcp-toolkit`.

## Overview

The toolkit is organized around a single server object that exposes the same
tool catalog through multiple transports:

- MCP
- HTTP API
- remote CLI (`lean-cli-toolkit`)
- local shell (`lean-mcp-toolkit shell`)

The implementation keeps the transport layer thin and concentrates the actual
tool logic in service and backend layers.

## Main Layers

### 1. Server / transport layer

Key entrypoints:

- `ToolkitServer`
- FastAPI app construction
- MCP server registration
- HTTP client wrappers
- CLI and shell entrypoints

Responsibilities:

- load configuration
- wire active groups
- expose tool metadata
- dispatch requests to local services
- expose HTTP and MCP surfaces

### 2. Group plugin layer

Each tool family is packaged as a group plugin. A group plugin defines:

- backend dependencies
- local service construction
- HTTP client construction
- tool specs
- MCP registrations
- HTTP/local handlers

This is the layer that keeps:

- one canonical tool spec
- one handler map
- one local service implementation

while supporting multiple transports.

### 3. Service layer

Each group has a local service implementation that owns the actual tool
behavior. Examples:

- diagnostics
- declarations
- LSP groups
- search groups

This layer is transport-independent.

### 4. Backend layer

The backend layer provides reusable execution/runtime capabilities such as:

- Lean command runtime
- target resolution
- LeanInteract runtime
- LSP client manager
- LeanExplore adapters
- external search-provider adapters
- lightweight `text_ast` analysis helpers

Heavy resources such as subprocesses, client pools, or long-lived managers are
kept here.

### 5. Interface layer

Selected capabilities have an internal interface layer that normalizes multiple
backend implementations behind one capability-oriented API.

Current examples include:

- declaration extraction
- no-sorry checks
- direct axiom declaration checks

This layer lets group services switch implementations without changing the
transport or tool contracts.

## Transport Sharing

The toolkit intentionally shares contracts across:

- MCP tools
- HTTP JSON endpoints
- CLI command help and payload mapping

`/api/v1/meta/tools` is the canonical discovery endpoint for exposed tool
metadata. The remote CLI uses it to build the live command tree dynamically.

## Backend Categories

### Heavy / runtime-oriented backends

- Lean command runtime
- LeanInteract runtime
- LSP client manager
- LeanExplore local or remote adapters
- external search providers

These backends may manage:

- subprocesses
- pools
- cached sessions
- network clients

### Lightweight source-analysis backends

The `text_ast` backend provides fast source-oriented analysis for cases where
full elaboration is not required. It is currently used to support:

- text-based no-sorry checks
- declaration extraction
- direct axiom declaration checks

## Tool Naming

Tools are documented by canonical names, but visible aliases depend on:

- group activation
- naming mode
- include/exclude filters

This is why the remote CLI builds its command tree from the live server rather
than from a hard-coded static list.

## Related Documents

- [../usage/README.md](../usage/README.md)
- [../tool_catalog/tool_reference.md](../tool_catalog/tool_reference.md)
- [../configuration/README.md](../configuration/README.md)

