"""Lean-backed direct axiom declaration interface wrapper.

This preserves the historical Lean-oriented direct-risk scan and serves as the
semantic comparison point for the lighter ``text_ast`` backend.
"""

from __future__ import annotations

from collections.abc import Callable

from ..base import AxiomDeclsInterfaceRequest, AxiomDeclsInterfaceResponse


class LeanAxiomDeclsInterfaceBackend:
    """Thin adapter around the legacy Lean-backed direct-risk runner."""

    backend_name = "lean"

    def __init__(self, *, runner: Callable[[AxiomDeclsInterfaceRequest], AxiomDeclsInterfaceResponse]) -> None:
        self.runner = runner

    def run(self, req: AxiomDeclsInterfaceRequest) -> AxiomDeclsInterfaceResponse:
        return self.runner(req)


__all__ = ["LeanAxiomDeclsInterfaceBackend"]
