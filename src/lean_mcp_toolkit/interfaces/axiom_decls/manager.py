"""Manager for direct axiom declaration check interface backends.

The manager only abstracts direct declaration/alias scanning. It does not
replace the separate probe-based axiom usage audit performed later in the
diagnostics pipeline.
"""

from __future__ import annotations

from collections.abc import Callable

from .backends import LeanAxiomDeclsInterfaceBackend, TextAstAxiomDeclsInterfaceBackend
from .base import AxiomDeclsInterfaceBackend, AxiomDeclsInterfaceRequest, AxiomDeclsInterfaceResponse


class AxiomDeclsInterfaceManager:
    """Dispatch direct declaration-risk checks to the configured backend."""

    def __init__(
        self,
        *,
        backend_name: str,
        lean_runner: Callable[[AxiomDeclsInterfaceRequest], AxiomDeclsInterfaceResponse],
        backends: dict[str, AxiomDeclsInterfaceBackend] | None = None,
    ) -> None:
        self.backend_name = backend_name
        self.backends = backends or {
            "text_ast": TextAstAxiomDeclsInterfaceBackend(),
            "lean": LeanAxiomDeclsInterfaceBackend(runner=lean_runner),
        }

    def run(self, req: AxiomDeclsInterfaceRequest) -> AxiomDeclsInterfaceResponse:
        backend = self.backends.get(self.backend_name)
        if backend is None:
            return AxiomDeclsInterfaceResponse(
                success=False,
                error_message=f"unsupported axiom declaration backend: {self.backend_name}",
                declared_axioms=tuple(),
                alias_exports=tuple(),
            )
        return backend.run(req)


__all__ = ["AxiomDeclsInterfaceManager"]
