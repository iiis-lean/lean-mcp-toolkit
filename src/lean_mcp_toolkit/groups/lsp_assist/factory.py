"""Factories for lsp_assist local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import LspAssistHttpClient
from .service_impl import LspAssistServiceImpl


def create_lsp_assist_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> LspAssistServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    manager = backends.get(BackendKey.LSP_CLIENT_MANAGER) if backends is not None else None
    return LspAssistServiceImpl(config=resolved, lsp_client_manager=manager)


def create_lsp_assist_client(*, http_config: HttpConfig) -> LspAssistHttpClient:
    return LspAssistHttpClient(http_config=http_config)


__all__ = ["create_lsp_assist_service", "create_lsp_assist_client"]

