"""HTTP-backed lsp_core client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_core import (
    LspCodeActionsRequest,
    LspCodeActionsResponse,
    LspFileOutlineRequest,
    LspFileOutlineResponse,
    LspGoalRequest,
    LspGoalResponse,
    LspHoverRequest,
    LspHoverResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    LspTermGoalRequest,
    LspTermGoalResponse,
)
from ...core.services import LspCoreService
from ...transport.http import HttpConfig, HttpJsonClient


class LspCoreHttpClient(LspCoreService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_file_outline(
        self,
        req: LspFileOutlineRequest,
    ) -> LspFileOutlineResponse:
        data = self._post("/lsp/file_outline", req.to_dict())
        return LspFileOutlineResponse.from_dict(data)

    def run_goal(self, req: LspGoalRequest) -> LspGoalResponse:
        data = self._post("/lsp/goal", req.to_dict())
        return LspGoalResponse.from_dict(data)

    def run_term_goal(
        self,
        req: LspTermGoalRequest,
    ) -> LspTermGoalResponse:
        data = self._post("/lsp/term_goal", req.to_dict())
        return LspTermGoalResponse.from_dict(data)

    def run_hover(self, req: LspHoverRequest) -> LspHoverResponse:
        data = self._post("/lsp/hover", req.to_dict())
        return LspHoverResponse.from_dict(data)

    def run_code_actions(
        self,
        req: LspCodeActionsRequest,
    ) -> LspCodeActionsResponse:
        data = self._post("/lsp/code_actions", req.to_dict())
        return LspCodeActionsResponse.from_dict(data)

    def run_snippet(self, req: LspRunSnippetRequest) -> LspRunSnippetResponse:
        data = self._post("/lsp/run_snippet", req.to_dict())
        return LspRunSnippetResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)

__all__ = ["LspCoreHttpClient"]
