"""Factories for search_core local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import SearchCoreHttpClient
from .service_impl import SearchCoreServiceImpl


def create_search_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> SearchCoreServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    lean_explore_backend = (
        backends.get(BackendKey.LEAN_EXPLORE_BACKEND) if backends is not None else None
    )
    return SearchCoreServiceImpl(
        config=resolved,
        lean_explore_backend=lean_explore_backend,
    )


def create_search_core_client(*, http_config: HttpConfig) -> SearchCoreHttpClient:
    return SearchCoreHttpClient(http_config=http_config)


__all__ = ["create_search_core_service", "create_search_core_client"]
