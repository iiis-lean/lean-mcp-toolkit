"""Unified runtime wrapper for local/http toolkit usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .app import create_local_toolkit_server, create_toolkit_http_client
from .config import ToolkitConfig, load_toolkit_config
from .contracts.base import JsonDict
from .core.services import DeclarationsService, DiagnosticsService, LspCoreService, SearchCoreService
from .transport.http import HttpConfig

ToolkitRuntimeMode = Literal["local", "http"]


class ToolkitInvoker(Protocol):
    """Tool-style invoker API shared by local and http runtime handles."""

    diagnostics: DiagnosticsService | None
    declarations: DeclarationsService | None
    lsp_core: LspCoreService | None
    search_core: SearchCoreService | None

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        ...


@dataclass(slots=True)
class ToolkitRuntime:
    """Lightweight unified runtime for both local service and HTTP client."""

    mode: ToolkitRuntimeMode
    config: ToolkitConfig
    diagnostics: DiagnosticsService | None
    declarations: DeclarationsService | None
    lsp_core: LspCoreService | None
    search_core: SearchCoreService | None
    toolkit: ToolkitInvoker
    http_config: HttpConfig | None = None

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        return self.toolkit.dispatch_api(route_path, payload)


def create_toolkit_runtime(
    *,
    mode: ToolkitRuntimeMode,
    config_path: str | None = None,
    http_base_url_override: str | None = None,
) -> ToolkitRuntime:
    """Create toolkit runtime with unified shape for local/http modes."""

    config = load_toolkit_config(config_path=config_path)

    if mode == "local":
        server = create_local_toolkit_server(config=config)
        return ToolkitRuntime(
            mode="local",
            config=config,
            diagnostics=server.diagnostics,
            declarations=server.declarations,
            lsp_core=server.lsp_core,
            search_core=server.search_core,
            toolkit=server,
            http_config=None,
        )

    if mode == "http":
        http_config = _resolve_http_config(
            config=config,
            http_base_url_override=http_base_url_override,
        )
        toolkit_client = create_toolkit_http_client(http_config=http_config, config=config)
        return ToolkitRuntime(
            mode="http",
            config=config,
            diagnostics=toolkit_client.diagnostics,
            declarations=toolkit_client.declarations,
            lsp_core=toolkit_client.lsp_core,
            search_core=toolkit_client.search_core,
            toolkit=toolkit_client,
            http_config=http_config,
        )

    raise ValueError(f"unsupported runtime mode: {mode}")


def _resolve_http_config(
    *,
    config: ToolkitConfig,
    http_base_url_override: str | None,
) -> HttpConfig:
    raw = (http_base_url_override or "").strip()
    if raw:
        base_url = raw.rstrip("/")
    else:
        base_url = f"http://{config.server.host}:{config.server.port}"
    timeout = (
        float(config.server.default_timeout_seconds)
        if config.server.default_timeout_seconds is not None
        else 30.0
    )
    return HttpConfig(
        base_url=base_url,
        api_prefix=config.server.api_prefix,
        timeout_seconds=timeout,
    )


__all__ = ["ToolkitRuntime", "ToolkitRuntimeMode", "create_toolkit_runtime"]
