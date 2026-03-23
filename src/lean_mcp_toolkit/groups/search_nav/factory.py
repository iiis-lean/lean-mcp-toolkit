"""Factories for search_nav local service and HTTP client."""

from __future__ import annotations

from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import SearchNavHttpClient
from .service_impl import SearchNavServiceImpl


def create_search_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchNavServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    return SearchNavServiceImpl(config=resolved)


def create_search_nav_client(*, http_config: HttpConfig) -> SearchNavHttpClient:
    return SearchNavHttpClient(http_config=http_config)


__all__ = ["create_search_nav_service", "create_search_nav_client"]
