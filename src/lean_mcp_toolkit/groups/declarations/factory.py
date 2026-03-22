"""Factories for declarations local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import DeclarationsHttpClient
from .service_impl import DeclarationsServiceImpl


def create_declarations_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> DeclarationsServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    backend_map = backends.get(BackendKey.DECLARATIONS_BACKENDS) if backends is not None else None
    lsp_client_manager = (
        backends.get(BackendKey.LSP_CLIENT_MANAGER) if backends is not None else None
    )
    return DeclarationsServiceImpl(
        config=resolved,
        backends=backend_map,
        lsp_client_manager=lsp_client_manager,
    )


def create_declarations_client(
    *,
    http_config: HttpConfig,
) -> DeclarationsHttpClient:
    return DeclarationsHttpClient(http_config=http_config)
