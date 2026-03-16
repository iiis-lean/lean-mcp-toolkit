"""Factories for local services and HTTP clients."""

from __future__ import annotations

from ..config import ToolkitConfig, load_toolkit_config
from ..groups import GroupPlugin
from ..groups.diagnostics import (
    DiagnosticsHttpClient,
    DiagnosticsServiceImpl,
    create_diagnostics_client as _create_group_diagnostics_client,
    create_diagnostics_service as _create_group_diagnostics_service,
)
from ..transport.http import HttpConfig
from .toolkit_client import ToolkitHttpClient
from .toolkit_server import ToolkitServer



def create_local_toolkit_server(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> ToolkitServer:
    resolved = config or load_toolkit_config(config_path=config_path)
    return ToolkitServer.from_config(resolved)



def create_toolkit_http_client(
    *,
    http_config: HttpConfig,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    plugins: tuple[GroupPlugin, ...] | None = None,
) -> ToolkitHttpClient:
    resolved = config or load_toolkit_config(config_path=config_path)
    return ToolkitHttpClient.from_http_config(
        http_config,
        config=resolved,
        plugins=plugins,
    )



def create_default_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DiagnosticsServiceImpl:
    return _create_group_diagnostics_service(config=config, config_path=config_path)



def create_default_diagnostics_client(*, http_config: HttpConfig) -> DiagnosticsHttpClient:
    return _create_group_diagnostics_client(http_config=http_config)


def create_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DiagnosticsServiceImpl:
    return create_default_diagnostics_service(config=config, config_path=config_path)


def create_diagnostics_client(*, http_config: HttpConfig) -> DiagnosticsHttpClient:
    return create_default_diagnostics_client(http_config=http_config)


__all__ = [
    "create_local_toolkit_server",
    "create_toolkit_http_client",
    "create_default_diagnostics_service",
    "create_default_diagnostics_client",
    "create_diagnostics_service",
    "create_diagnostics_client",
]
