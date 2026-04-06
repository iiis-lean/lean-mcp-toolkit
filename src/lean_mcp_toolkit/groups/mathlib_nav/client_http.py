"""HTTP-backed mathlib_nav client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavFileOutlineResponse,
    MathlibNavGrepRequest,
    MathlibNavGrepResponse,
    MathlibNavReadRequest,
    MathlibNavReadResponse,
    MathlibNavTreeRequest,
    MathlibNavTreeResponse,
)
from ...core.services import MathlibNavService
from ...transport.http import HttpConfig, HttpJsonClient


class MathlibNavHttpClient(MathlibNavService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_mathlib_nav_tree(self, req: MathlibNavTreeRequest) -> MathlibNavTreeResponse:
        return MathlibNavTreeResponse.from_dict(self._post("/search/mathlib_nav/tree", req.to_dict()))

    def run_mathlib_nav_file_outline(
        self,
        req: MathlibNavFileOutlineRequest,
    ) -> MathlibNavFileOutlineResponse:
        return MathlibNavFileOutlineResponse.from_dict(
            self._post("/search/mathlib_nav/file_outline", req.to_dict())
        )

    def run_mathlib_nav_grep(self, req: MathlibNavGrepRequest) -> MathlibNavGrepResponse:
        return MathlibNavGrepResponse.from_dict(
            self._post("/search/mathlib_nav/grep", req.to_dict())
        )

    def run_mathlib_nav_read(self, req: MathlibNavReadRequest) -> MathlibNavReadResponse:
        return MathlibNavReadResponse.from_dict(self._post("/search/mathlib_nav/read", req.to_dict()))

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["MathlibNavHttpClient"]
