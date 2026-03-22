"""Factories for diagnostics local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import DiagnosticsHttpClient
from .service_impl import DiagnosticsServiceImpl



def create_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> DiagnosticsServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    runtime = backends.get(BackendKey.LEAN_COMMAND_RUNTIME) if backends is not None else None
    resolver = backends.get(BackendKey.LEAN_TARGET_RESOLVER) if backends is not None else None
    declarations_backends = (
        backends.get(BackendKey.DECLARATIONS_BACKENDS)
        if backends is not None
        else None
    )
    return DiagnosticsServiceImpl(
        config=resolved,
        runtime=runtime,
        resolver=resolver,
        declarations_backends=declarations_backends,
    )



def create_diagnostics_client(
    *,
    http_config: HttpConfig,
) -> DiagnosticsHttpClient:
    return DiagnosticsHttpClient(http_config=http_config)
