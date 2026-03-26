"""Factories for proof_search_alt local service and HTTP client."""

from __future__ import annotations

from ...backends.context import BackendContext
from ...backends.keys import BackendKey
from ...config import ToolkitConfig, load_toolkit_config
from ...transport.http import HttpConfig
from .client_http import ProofSearchAltHttpClient
from .service_impl import ProofSearchAltServiceImpl


def create_proof_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
    backends: BackendContext | None = None,
) -> ProofSearchAltServiceImpl:
    resolved = config or load_toolkit_config(config_path=config_path)
    lsp_manager = backends.get(BackendKey.LSP_CLIENT_MANAGER) if backends is not None else None
    backend_manager = (
        backends.get(BackendKey.PROOF_SEARCH_ALT_MANAGER) if backends is not None else None
    )
    return ProofSearchAltServiceImpl(
        config=resolved,
        lsp_client_manager=lsp_manager,
        backend_manager=backend_manager,
    )


def create_proof_search_alt_client(*, http_config: HttpConfig) -> ProofSearchAltHttpClient:
    return ProofSearchAltHttpClient(http_config=http_config)


__all__ = ["create_proof_search_alt_service", "create_proof_search_alt_client"]

