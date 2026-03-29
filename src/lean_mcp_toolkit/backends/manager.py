"""Backend initialization manager."""

from __future__ import annotations

from ..config import ToolkitConfig
from .context import BackendContext
from .declarations import LeanInteractDeclarationsBackend, SimpleLeanDeclarationsBackend
from .keys import BackendKey
from .lean import LeanCommandRuntime
from .lean.path import TargetResolver
from .lean_explore import LeanExploreBackendAdapter
from .lsp import LeanLSPClientManager
from .search_providers import ProofSearchAltBackendManager, SearchAltBackendManager


def build_backend_context(
    *,
    config: ToolkitConfig,
    required_backend_keys: tuple[str, ...] | list[str],
) -> BackendContext:
    """Build backend context for active groups only."""

    required = {key.strip() for key in required_backend_keys if key and key.strip()}
    context = BackendContext()

    if BackendKey.LEAN_COMMAND_RUNTIME in required:
        context.set(
            BackendKey.LEAN_COMMAND_RUNTIME,
            LeanCommandRuntime(
                backend_config=config.backends.lean_command,
                toolchain_config=config.toolchain,
            ),
        )

    if BackendKey.LEAN_TARGET_RESOLVER in required:
        context.set(BackendKey.LEAN_TARGET_RESOLVER, TargetResolver())

    if BackendKey.DECLARATIONS_BACKENDS in required:
        context.set(
            BackendKey.DECLARATIONS_BACKENDS,
            {
                "lean_interact": LeanInteractDeclarationsBackend(
                    toolchain_config=config.toolchain,
                    backend_config=config.backends.lean_interact,
                ),
                "simple_lean": SimpleLeanDeclarationsBackend(),
                "native": SimpleLeanDeclarationsBackend(),
            },
        )

    if BackendKey.LSP_CLIENT_MANAGER in required:
        context.set(
            BackendKey.LSP_CLIENT_MANAGER,
            LeanLSPClientManager(backend_config=config.backends.lsp),
        )

    if BackendKey.LEAN_EXPLORE_BACKEND in required:
        context.set(
            BackendKey.LEAN_EXPLORE_BACKEND,
            LeanExploreBackendAdapter(
                backend_config=config.backends.lean_explore,
                search_config=config.search_core,
            ),
        )

    if BackendKey.SEARCH_ALT_MANAGER in required:
        context.set(
            BackendKey.SEARCH_ALT_MANAGER,
            SearchAltBackendManager(config=config.backends.search_providers),
        )

    if BackendKey.PROOF_SEARCH_ALT_MANAGER in required:
        context.set(
            BackendKey.PROOF_SEARCH_ALT_MANAGER,
            ProofSearchAltBackendManager(config=config.backends.search_providers),
        )

    return context


__all__ = ["build_backend_context"]
