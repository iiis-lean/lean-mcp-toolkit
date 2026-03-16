"""Factories for diagnostics local service and HTTP client."""

from __future__ import annotations

from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import DiagnosticsHttpClient
from .service_impl import DiagnosticsServiceImpl



def create_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DiagnosticsServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    return DiagnosticsServiceImpl(config=resolved)



def create_diagnostics_client(
    *,
    http_config: HttpConfig,
) -> DiagnosticsHttpClient:
    return DiagnosticsHttpClient(http_config=http_config)
