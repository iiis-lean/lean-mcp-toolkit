"""HTTP-backed lsp_heavy client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspProofProfileResponse,
    LspWidgetSourceRequest,
    LspWidgetSourceResponse,
    LspWidgetsRequest,
    LspWidgetsResponse,
)
from ...core.services import LspHeavyService
from ...transport.http import HttpConfig, HttpJsonClient


class LspHeavyHttpClient(LspHeavyService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_widgets(self, req: LspWidgetsRequest) -> LspWidgetsResponse:
        data = self._post("/lsp/widgets", req.to_dict())
        return LspWidgetsResponse.from_dict(data)

    def run_widget_source(self, req: LspWidgetSourceRequest) -> LspWidgetSourceResponse:
        data = self._post("/lsp/widget_source", req.to_dict())
        return LspWidgetSourceResponse.from_dict(data)

    def run_proof_profile(self, req: LspProofProfileRequest) -> LspProofProfileResponse:
        data = self._post("/lsp/proof_profile", req.to_dict())
        return LspProofProfileResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["LspHeavyHttpClient"]
