"""Factories for local services and HTTP clients."""

from __future__ import annotations

from ..config import ToolkitConfig, load_toolkit_config
from ..groups import GroupPlugin
from ..groups.build_base import (
    BuildBaseHttpClient,
    BuildBaseServiceImpl,
    create_build_base_client as _create_group_build_base_client,
    create_build_base_service as _create_group_build_base_service,
)
from ..groups.declarations import (
    DeclarationsHttpClient,
    DeclarationsServiceImpl,
    create_declarations_client as _create_group_declarations_client,
    create_declarations_service as _create_group_declarations_service,
)
from ..groups.diagnostics import (
    DiagnosticsHttpClient,
    DiagnosticsServiceImpl,
    create_diagnostics_client as _create_group_diagnostics_client,
    create_diagnostics_service as _create_group_diagnostics_service,
)
from ..groups.lsp_core import (
    LspCoreHttpClient,
    LspCoreServiceImpl,
    create_lsp_core_client as _create_group_lsp_core_client,
    create_lsp_core_service as _create_group_lsp_core_service,
)
from ..groups.lsp_assist import (
    LspAssistHttpClient,
    LspAssistServiceImpl,
    create_lsp_assist_client as _create_group_lsp_assist_client,
    create_lsp_assist_service as _create_group_lsp_assist_service,
)
from ..groups.lsp_heavy import (
    LspHeavyHttpClient,
    LspHeavyServiceImpl,
    create_lsp_heavy_client as _create_group_lsp_heavy_client,
    create_lsp_heavy_service as _create_group_lsp_heavy_service,
)
from ..groups.mathlib_nav import (
    MathlibNavHttpClient,
    MathlibNavServiceImpl,
    create_mathlib_nav_client as _create_group_mathlib_nav_client,
    create_mathlib_nav_service as _create_group_mathlib_nav_service,
)
from ..groups.proof_search_alt import (
    ProofSearchAltHttpClient,
    ProofSearchAltServiceImpl,
    create_proof_search_alt_client as _create_group_proof_search_alt_client,
    create_proof_search_alt_service as _create_group_proof_search_alt_service,
)
from ..groups.search_alt import (
    SearchAltHttpClient,
    SearchAltServiceImpl,
    create_search_alt_client as _create_group_search_alt_client,
    create_search_alt_service as _create_group_search_alt_service,
)
from ..groups.search_core import (
    SearchCoreHttpClient,
    SearchCoreServiceImpl,
    create_search_core_client as _create_group_search_core_client,
    create_search_core_service as _create_group_search_core_service,
)
from ..groups.search_nav import (
    SearchNavHttpClient,
    SearchNavServiceImpl,
    create_search_nav_client as _create_group_search_nav_client,
    create_search_nav_service as _create_group_search_nav_service,
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


def create_default_build_base_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> BuildBaseServiceImpl:
    return _create_group_build_base_service(config=config, config_path=config_path)


def create_default_build_base_client(*, http_config: HttpConfig) -> BuildBaseHttpClient:
    return _create_group_build_base_client(http_config=http_config)



def create_default_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DiagnosticsServiceImpl:
    return _create_group_diagnostics_service(config=config, config_path=config_path)



def create_default_diagnostics_client(*, http_config: HttpConfig) -> DiagnosticsHttpClient:
    return _create_group_diagnostics_client(http_config=http_config)


def create_default_declarations_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DeclarationsServiceImpl:
    return _create_group_declarations_service(config=config, config_path=config_path)


def create_default_declarations_client(*, http_config: HttpConfig) -> DeclarationsHttpClient:
    return _create_group_declarations_client(http_config=http_config)


def create_default_lsp_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspCoreServiceImpl:
    return _create_group_lsp_core_service(config=config, config_path=config_path)


def create_default_lsp_core_client(*, http_config: HttpConfig) -> LspCoreHttpClient:
    return _create_group_lsp_core_client(http_config=http_config)


def create_default_lsp_assist_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspAssistServiceImpl:
    return _create_group_lsp_assist_service(config=config, config_path=config_path)


def create_default_lsp_assist_client(*, http_config: HttpConfig) -> LspAssistHttpClient:
    return _create_group_lsp_assist_client(http_config=http_config)


def create_default_lsp_heavy_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspHeavyServiceImpl:
    return _create_group_lsp_heavy_service(config=config, config_path=config_path)


def create_default_lsp_heavy_client(*, http_config: HttpConfig) -> LspHeavyHttpClient:
    return _create_group_lsp_heavy_client(http_config=http_config)


def create_default_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchAltServiceImpl:
    return _create_group_search_alt_service(config=config, config_path=config_path)


def create_default_search_alt_client(*, http_config: HttpConfig) -> SearchAltHttpClient:
    return _create_group_search_alt_client(http_config=http_config)


def create_default_search_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchCoreServiceImpl:
    return _create_group_search_core_service(config=config, config_path=config_path)


def create_default_search_core_client(*, http_config: HttpConfig) -> SearchCoreHttpClient:
    return _create_group_search_core_client(http_config=http_config)


def create_default_search_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchNavServiceImpl:
    return _create_group_search_nav_service(config=config, config_path=config_path)


def create_default_search_nav_client(*, http_config: HttpConfig) -> SearchNavHttpClient:
    return _create_group_search_nav_client(http_config=http_config)


def create_default_mathlib_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> MathlibNavServiceImpl:
    return _create_group_mathlib_nav_service(config=config, config_path=config_path)


def create_default_mathlib_nav_client(*, http_config: HttpConfig) -> MathlibNavHttpClient:
    return _create_group_mathlib_nav_client(http_config=http_config)


def create_default_proof_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> ProofSearchAltServiceImpl:
    return _create_group_proof_search_alt_service(config=config, config_path=config_path)


def create_default_proof_search_alt_client(
    *,
    http_config: HttpConfig,
) -> ProofSearchAltHttpClient:
    return _create_group_proof_search_alt_client(http_config=http_config)


def create_build_base_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> BuildBaseServiceImpl:
    return create_default_build_base_service(config=config, config_path=config_path)


def create_build_base_client(*, http_config: HttpConfig) -> BuildBaseHttpClient:
    return create_default_build_base_client(http_config=http_config)


def create_diagnostics_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DiagnosticsServiceImpl:
    return create_default_diagnostics_service(config=config, config_path=config_path)


def create_diagnostics_client(*, http_config: HttpConfig) -> DiagnosticsHttpClient:
    return create_default_diagnostics_client(http_config=http_config)


def create_declarations_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> DeclarationsServiceImpl:
    return create_default_declarations_service(config=config, config_path=config_path)


def create_declarations_client(*, http_config: HttpConfig) -> DeclarationsHttpClient:
    return create_default_declarations_client(http_config=http_config)


def create_lsp_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspCoreServiceImpl:
    return create_default_lsp_core_service(config=config, config_path=config_path)


def create_lsp_core_client(*, http_config: HttpConfig) -> LspCoreHttpClient:
    return create_default_lsp_core_client(http_config=http_config)


def create_lsp_assist_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspAssistServiceImpl:
    return create_default_lsp_assist_service(config=config, config_path=config_path)


def create_lsp_assist_client(*, http_config: HttpConfig) -> LspAssistHttpClient:
    return create_default_lsp_assist_client(http_config=http_config)


def create_lsp_heavy_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> LspHeavyServiceImpl:
    return create_default_lsp_heavy_service(config=config, config_path=config_path)


def create_lsp_heavy_client(*, http_config: HttpConfig) -> LspHeavyHttpClient:
    return create_default_lsp_heavy_client(http_config=http_config)


def create_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchAltServiceImpl:
    return create_default_search_alt_service(config=config, config_path=config_path)


def create_search_alt_client(*, http_config: HttpConfig) -> SearchAltHttpClient:
    return create_default_search_alt_client(http_config=http_config)


def create_search_core_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchCoreServiceImpl:
    return create_default_search_core_service(config=config, config_path=config_path)


def create_search_core_client(*, http_config: HttpConfig) -> SearchCoreHttpClient:
    return create_default_search_core_client(http_config=http_config)


def create_search_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> SearchNavServiceImpl:
    return create_default_search_nav_service(config=config, config_path=config_path)


def create_search_nav_client(*, http_config: HttpConfig) -> SearchNavHttpClient:
    return create_default_search_nav_client(http_config=http_config)


def create_mathlib_nav_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> MathlibNavServiceImpl:
    return create_default_mathlib_nav_service(config=config, config_path=config_path)


def create_mathlib_nav_client(*, http_config: HttpConfig) -> MathlibNavHttpClient:
    return create_default_mathlib_nav_client(http_config=http_config)


def create_proof_search_alt_service(
    *,
    config: ToolkitConfig | None = None,
    config_path: str | None = None,
) -> ProofSearchAltServiceImpl:
    return create_default_proof_search_alt_service(config=config, config_path=config_path)


def create_proof_search_alt_client(
    *,
    http_config: HttpConfig,
) -> ProofSearchAltHttpClient:
    return create_default_proof_search_alt_client(http_config=http_config)


__all__ = [
    "create_local_toolkit_server",
    "create_toolkit_http_client",
    "create_default_build_base_service",
    "create_default_build_base_client",
    "create_default_diagnostics_service",
    "create_default_diagnostics_client",
    "create_default_declarations_service",
    "create_default_declarations_client",
    "create_default_lsp_core_service",
    "create_default_lsp_core_client",
    "create_default_lsp_assist_service",
    "create_default_lsp_assist_client",
    "create_default_lsp_heavy_service",
    "create_default_lsp_heavy_client",
    "create_default_search_alt_service",
    "create_default_search_alt_client",
    "create_default_search_core_service",
    "create_default_search_core_client",
    "create_default_mathlib_nav_service",
    "create_default_mathlib_nav_client",
    "create_default_search_nav_service",
    "create_default_search_nav_client",
    "create_default_proof_search_alt_service",
    "create_default_proof_search_alt_client",
    "create_build_base_service",
    "create_build_base_client",
    "create_diagnostics_service",
    "create_diagnostics_client",
    "create_declarations_service",
    "create_declarations_client",
    "create_lsp_core_service",
    "create_lsp_core_client",
    "create_lsp_assist_service",
    "create_lsp_assist_client",
    "create_lsp_heavy_service",
    "create_lsp_heavy_client",
    "create_search_alt_service",
    "create_search_alt_client",
    "create_search_core_service",
    "create_search_core_client",
    "create_mathlib_nav_service",
    "create_mathlib_nav_client",
    "create_search_nav_service",
    "create_search_nav_client",
    "create_proof_search_alt_service",
    "create_proof_search_alt_client",
]
