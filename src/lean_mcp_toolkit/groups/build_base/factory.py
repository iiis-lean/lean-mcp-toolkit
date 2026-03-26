"""Factories for build_base local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import BuildBaseHttpClient
from .service_impl import BuildBaseServiceImpl


def create_build_base_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> BuildBaseServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    runtime = backends.get(BackendKey.LEAN_COMMAND_RUNTIME) if backends is not None else None
    resolver = backends.get(BackendKey.LEAN_TARGET_RESOLVER) if backends is not None else None
    return BuildBaseServiceImpl(
        config=resolved,
        runtime=runtime,
        resolver=resolver,
    )


def create_build_base_client(
    *,
    http_config: HttpConfig,
) -> BuildBaseHttpClient:
    return BuildBaseHttpClient(http_config=http_config)
