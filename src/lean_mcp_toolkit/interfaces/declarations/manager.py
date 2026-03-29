"""Manager for unified declarations interface.

This manager centralizes backend selection so group-level code does not need to
know whether declarations come from LeanInteract, a future simple Lean-based
extractor, or the lightweight text/AST parser.
"""

from __future__ import annotations

from pathlib import Path

from ...backends.declarations import LeanInteractDeclarationsBackend
from ...config import LeanInteractBackendConfig, ToolkitConfig, ToolchainConfig
from .backends import (
    LeanInteractDeclarationsInterfaceBackend,
    SimpleLeanDeclarationsInterfaceBackend,
    TextAstDeclarationsInterfaceBackend,
)
from .base import DeclarationsInterfaceBackend, DeclarationsInterfaceRequest, DeclarationsInterfaceResponse


class DeclarationsInterfaceManager:
    """Dispatch declaration extraction to the configured backend.

    Backend characteristics:
    - ``lean_interact``: highest fidelity, heaviest dependency footprint.
    - ``text_ast``: fastest default for source-oriented workflows.
    - ``simple_lean``: placeholder for a future middle-ground backend.
    """

    def __init__(
        self,
        *,
        config: ToolkitConfig,
        backends: dict[str, DeclarationsInterfaceBackend] | None = None,
    ) -> None:
        self.config = config
        self.backends = backends or self._build_default_backends(
            toolchain_config=config.toolchain,
            lean_interact_config=config.backends.lean_interact,
            include_value=config.declarations.default_include_value,
        )

    def extract(self, req: DeclarationsInterfaceRequest) -> DeclarationsInterfaceResponse:
        backend = self.backends.get(self.config.declarations.default_backend)
        if backend is None:
            return DeclarationsInterfaceResponse(
                success=False,
                error_message=f"unsupported declarations backend: {self.config.declarations.default_backend}",
                declarations=tuple(),
            )
        return backend.extract(req)

    def extract_batch(
        self,
        reqs: tuple[DeclarationsInterfaceRequest, ...],
    ) -> tuple[DeclarationsInterfaceResponse, ...]:
        backend = self.backends.get(self.config.declarations.default_backend)
        if backend is None:
            error = f"unsupported declarations backend: {self.config.declarations.default_backend}"
            return tuple(
                DeclarationsInterfaceResponse(
                    success=False,
                    error_message=error,
                    declarations=tuple(),
                )
                for _ in reqs
            )
        return backend.extract_batch(reqs)

    @staticmethod
    def _build_default_backends(
        *,
        toolchain_config: ToolchainConfig,
        lean_interact_config: LeanInteractBackendConfig,
        include_value: bool,
    ) -> dict[str, DeclarationsInterfaceBackend]:
        lean_interact = LeanInteractDeclarationsBackend(
            toolchain_config=toolchain_config,
            backend_config=lean_interact_config,
        )
        return {
            "text_ast": TextAstDeclarationsInterfaceBackend(include_value=include_value),
            "simple_lean": SimpleLeanDeclarationsInterfaceBackend(),
            "lean_interact": LeanInteractDeclarationsInterfaceBackend(
                backend=lean_interact,
                include_value=include_value,
            ),
        }


__all__ = ["DeclarationsInterfaceManager"]
