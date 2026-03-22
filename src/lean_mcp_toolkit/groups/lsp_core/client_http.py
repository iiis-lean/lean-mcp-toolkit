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
    LspTermGoalRequest,
    LspTermGoalResponse,
    MarkdownResponse,
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
    ) -> LspFileOutlineResponse | MarkdownResponse:
        data = self._post("/lsp/file_outline", req.to_dict())
        return _parse_lsp_response(data, LspFileOutlineResponse)

    def run_goal(self, req: LspGoalRequest) -> LspGoalResponse | MarkdownResponse:
        data = self._post("/lsp/goal", req.to_dict())
        return _parse_lsp_response(data, LspGoalResponse)

    def run_term_goal(
        self,
        req: LspTermGoalRequest,
    ) -> LspTermGoalResponse | MarkdownResponse:
        data = self._post("/lsp/term_goal", req.to_dict())
        return _parse_lsp_response(data, LspTermGoalResponse)

    def run_hover(self, req: LspHoverRequest) -> LspHoverResponse | MarkdownResponse:
        data = self._post("/lsp/hover", req.to_dict())
        return _parse_lsp_response(data, LspHoverResponse)

    def run_code_actions(
        self,
        req: LspCodeActionsRequest,
    ) -> LspCodeActionsResponse | MarkdownResponse:
        data = self._post("/lsp/code_actions", req.to_dict())
        return _parse_lsp_response(data, LspCodeActionsResponse)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


def _parse_lsp_response(data: JsonDict, cls):
    if "markdown" in data and "success" not in data:
        return MarkdownResponse.from_dict(data)
    return cls.from_dict(data)


__all__ = ["LspCoreHttpClient"]
