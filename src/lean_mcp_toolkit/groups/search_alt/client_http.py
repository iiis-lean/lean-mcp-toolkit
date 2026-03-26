"""HTTP-backed search_alt client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_alt import (
    SearchAltLeanDexRequest,
    SearchAltLeanDexResponse,
    SearchAltLeanFinderRequest,
    SearchAltLeanFinderResponse,
    SearchAltLeanSearchRequest,
    SearchAltLeanSearchResponse,
    SearchAltLoogleRequest,
    SearchAltLoogleResponse,
)
from ...core.services import SearchAltService
from ...transport.http import HttpConfig, HttpJsonClient


class SearchAltHttpClient(SearchAltService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_leansearch(self, req: SearchAltLeanSearchRequest) -> SearchAltLeanSearchResponse:
        return SearchAltLeanSearchResponse.from_dict(
            self._post("/search_alt/leansearch", req.to_dict())
        )

    def run_leandex(self, req: SearchAltLeanDexRequest) -> SearchAltLeanDexResponse:
        return SearchAltLeanDexResponse.from_dict(self._post("/search_alt/leandex", req.to_dict()))

    def run_loogle(self, req: SearchAltLoogleRequest) -> SearchAltLoogleResponse:
        return SearchAltLoogleResponse.from_dict(self._post("/search_alt/loogle", req.to_dict()))

    def run_leanfinder(self, req: SearchAltLeanFinderRequest) -> SearchAltLeanFinderResponse:
        return SearchAltLeanFinderResponse.from_dict(
            self._post("/search_alt/leanfinder", req.to_dict())
        )

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["SearchAltHttpClient"]

