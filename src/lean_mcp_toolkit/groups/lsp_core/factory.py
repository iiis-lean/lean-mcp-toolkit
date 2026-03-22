"""Factories for lsp_core local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import LspCoreHttpClient
from .service_impl import LspCoreServiceImpl


def create_lsp_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> LspCoreServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    manager = backends.get(BackendKey.LSP_CLIENT_MANAGER) if backends is not None else None
    return LspCoreServiceImpl(config=resolved, lsp_client_manager=manager)


def create_lsp_core_client(*, http_config: HttpConfig) -> LspCoreHttpClient:
    return LspCoreHttpClient(http_config=http_config)


__all__ = ["create_lsp_core_service", "create_lsp_core_client"]
