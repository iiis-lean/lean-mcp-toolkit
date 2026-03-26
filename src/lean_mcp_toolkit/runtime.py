"""Unified runtime wrapper for local/http toolkit usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .app import create_local_toolkit_server, create_toolkit_http_client
from .config import ToolkitConfig, load_toolkit_config
from .contracts.base import JsonDict
from .core.services import (
    BuildBaseService,
    DeclarationsService,
    DiagnosticsService,
    LspAssistService,
    LspHeavyService,
    LspCoreService,
    MathlibNavService,
    ProofSearchAltService,
    SearchAltService,
    SearchCoreService,
    SearchNavService,
)
from .transport.http import HttpConfig

ToolkitRuntimeMode = Literal["local", "http"]


class ToolkitInvoker(Protocol):
    """Tool-style invoker API shared by local and http runtime handles."""

    build_base: BuildBaseService | None
    diagnostics: DiagnosticsService | None
    declarations: DeclarationsService | None
    lsp_core: LspCoreService | None
    lsp_assist: LspAssistService | None
    lsp_heavy: LspHeavyService | None
    search_alt: SearchAltService | None
    search_core: SearchCoreService | None
    mathlib_nav: MathlibNavService | None
    search_nav: SearchNavService | None
    proof_search_alt: ProofSearchAltService | None

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        ...


@dataclass(slots=True)
class ToolkitRuntime:
    """Lightweight unified runtime for both local service and HTTP client."""

    mode: ToolkitRuntimeMode
    config: ToolkitConfig
    build_base: BuildBaseService | None
    diagnostics: DiagnosticsService | None
    declarations: DeclarationsService | None
    lsp_core: LspCoreService | None
    lsp_assist: LspAssistService | None
    lsp_heavy: LspHeavyService | None
    search_alt: SearchAltService | None
    search_core: SearchCoreService | None
    mathlib_nav: MathlibNavService | None
    search_nav: SearchNavService | None
    proof_search_alt: ProofSearchAltService | None
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
            build_base=getattr(server, "build_base", None),
            diagnostics=server.diagnostics,
            declarations=server.declarations,
            lsp_core=server.lsp_core,
            lsp_assist=getattr(server, "lsp_assist", None),
            lsp_heavy=getattr(server, "lsp_heavy", None),
            search_alt=getattr(server, "search_alt", None),
            search_core=server.search_core,
            mathlib_nav=getattr(server, "mathlib_nav", None),
            search_nav=server.search_nav,
            proof_search_alt=getattr(server, "proof_search_alt", None),
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
            build_base=getattr(toolkit_client, "build_base", None),
            diagnostics=toolkit_client.diagnostics,
            declarations=toolkit_client.declarations,
            lsp_core=toolkit_client.lsp_core,
            lsp_assist=getattr(toolkit_client, "lsp_assist", None),
            lsp_heavy=getattr(toolkit_client, "lsp_heavy", None),
            search_alt=getattr(toolkit_client, "search_alt", None),
            search_core=toolkit_client.search_core,
            mathlib_nav=getattr(toolkit_client, "mathlib_nav", None),
            search_nav=toolkit_client.search_nav,
            proof_search_alt=getattr(toolkit_client, "proof_search_alt", None),
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
