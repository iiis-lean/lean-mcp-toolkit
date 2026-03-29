"""Native backend placeholder for declarations extraction."""

from __future__ import annotations

from .base import DeclarationsBackendRequest, DeclarationsBackendResponse


class NativeDeclarationsBackend:
    """Placeholder backend; concrete logic is implemented in a dedicated branch."""

    backend_name = "native"

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        _ = req
        return DeclarationsBackendResponse(
            success=False,
            error_message="declarations backend `native` is not implemented",
            declarations=tuple(),
        )

    def extract_batch(
        self,
        reqs: tuple[DeclarationsBackendRequest, ...],
    ) -> tuple[DeclarationsBackendResponse, ...]:
        return tuple(self.extract(req) for req in reqs)
