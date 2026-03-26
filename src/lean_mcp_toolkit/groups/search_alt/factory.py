"""Factories for search_alt local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import SearchAltHttpClient
from .service_impl import SearchAltServiceImpl


def create_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> SearchAltServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    manager = backends.get(BackendKey.SEARCH_ALT_MANAGER) if backends is not None else None
    return SearchAltServiceImpl(config=resolved, backend_manager=manager)


def create_search_alt_client(*, http_config: HttpConfig) -> SearchAltHttpClient:
    return SearchAltHttpClient(http_config=http_config)


__all__ = ["create_search_alt_service", "create_search_alt_client"]

