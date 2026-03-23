"""Factories for mathlib_nav local service and HTTP client."""

from __future__ import annotations

from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import MathlibNavHttpClient
from .service_impl import MathlibNavServiceImpl


def create_mathlib_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> MathlibNavServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    return MathlibNavServiceImpl(config=resolved)


def create_mathlib_nav_client(*, http_config: HttpConfig) -> MathlibNavHttpClient:
    return MathlibNavHttpClient(http_config=http_config)


__all__ = ["create_mathlib_nav_service", "create_mathlib_nav_client"]
