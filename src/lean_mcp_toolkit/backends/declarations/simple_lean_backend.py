"""Simple Lean backend placeholder for declarations extraction."""

from __future__ import annotations

from .base import DeclarationsBackendRequest, DeclarationsBackendResponse


class SimpleLeanDeclarationsBackend:
    """Placeholder backend for a future simple Lean-based declarations path."""

    backend_name = "simple_lean"

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        _ = req
        return DeclarationsBackendResponse(
            success=False,
            error_message="declarations backend `simple_lean` is not implemented",
            declarations=tuple(),
        )

    def extract_batch(
        self,
        reqs: tuple[DeclarationsBackendRequest, ...],
    ) -> tuple[DeclarationsBackendResponse, ...]:
        return tuple(self.extract(req) for req in reqs)


__all__ = ["SimpleLeanDeclarationsBackend"]
