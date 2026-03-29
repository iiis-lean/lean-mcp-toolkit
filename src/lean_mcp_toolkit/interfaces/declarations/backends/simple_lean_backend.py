"""Placeholder simple Lean declarations backend.

This backend slot is reserved for a future lightweight Lean-native extractor
that would sit between ``text_ast`` and ``lean_interact`` in cost/fidelity.
"""

from __future__ import annotations

from ..base import DeclarationsInterfaceRequest, DeclarationsInterfaceResponse


class SimpleLeanDeclarationsInterfaceBackend:
    """Currently unimplemented declarations backend placeholder."""

    backend_name = "simple_lean"

    def extract(self, req: DeclarationsInterfaceRequest) -> DeclarationsInterfaceResponse:
        _ = req
        return DeclarationsInterfaceResponse(
            success=False,
            error_message="declarations backend `simple_lean` is not implemented",
            declarations=tuple(),
        )

    def extract_batch(
        self,
        reqs: tuple[DeclarationsInterfaceRequest, ...],
    ) -> tuple[DeclarationsInterfaceResponse, ...]:
        return tuple(self.extract(req) for req in reqs)


__all__ = ["SimpleLeanDeclarationsInterfaceBackend"]
