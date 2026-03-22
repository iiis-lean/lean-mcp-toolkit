"""HTTP-backed search_core client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_core import (
    LocalDeclSearchRequest,
    LocalDeclSearchResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
    MathlibDeclSearchRequest,
    MathlibDeclSearchResponse,
)
from ...core.services import SearchCoreService
from ...transport.http import HttpConfig, HttpJsonClient


class SearchCoreHttpClient(SearchCoreService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_mathlib_decl_search(
        self,
        req: MathlibDeclSearchRequest,
    ) -> MathlibDeclSearchResponse:
        data = self._post("/search/mathlib_decl/search", req.to_dict())
        return MathlibDeclSearchResponse.from_dict(data)

    def run_mathlib_decl_get(self, req: MathlibDeclGetRequest) -> MathlibDeclGetResponse:
        data = self._post("/search/mathlib_decl/get", req.to_dict())
        return MathlibDeclGetResponse.from_dict(data)

    def run_local_decl_search(self, req: LocalDeclSearchRequest) -> LocalDeclSearchResponse:
        data = self._post("/search/local_decl/search", req.to_dict())
        return LocalDeclSearchResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["SearchCoreHttpClient"]
