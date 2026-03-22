"""HTTP-backed declarations client implementing DeclarationsService protocol."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationLocateRequest,
    DeclarationLocateResponse,
)
from ...core.services import DeclarationsService
from ...transport.http import HttpConfig, HttpJsonClient


class DeclarationsHttpClient(DeclarationsService):
    """Declarations service-compatible HTTP client."""

    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def extract(self, req: DeclarationExtractRequest) -> DeclarationExtractResponse:
        payload = req.to_dict()
        data = self._post("/declarations/extract", payload)
        return DeclarationExtractResponse.from_dict(data)

    def locate(self, req: DeclarationLocateRequest) -> DeclarationLocateResponse:
        payload = req.to_dict()
        data = self._post("/declarations/locate", payload)
        return DeclarationLocateResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        result = self.http_client.post_json(path, payload)
        return result
