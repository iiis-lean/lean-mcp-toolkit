"""HTTP-backed lsp_assist client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_assist import (
    LspCompletionsRequest,
    LspCompletionsResponse,
    LspDeclarationSoundnessBatchRequest,
    LspDeclarationSoundnessBatchResponse,
    LspDeclarationSoundnessRequest,
    LspDeclarationSoundnessResponse,
    LspDeclarationFileRequest,
    LspDeclarationFileResponse,
    LspMultiAttemptRequest,
    LspMultiAttemptResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
)
from ...core.services import LspAssistService
from ...transport.http import HttpConfig, HttpJsonClient


class LspAssistHttpClient(LspAssistService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_completions(self, req: LspCompletionsRequest) -> LspCompletionsResponse:
        data = self._post("/lsp/completions", req.to_dict())
        return LspCompletionsResponse.from_dict(data)

    def run_declaration_file(
        self,
        req: LspDeclarationFileRequest,
    ) -> LspDeclarationFileResponse:
        data = self._post("/lsp/declaration_file", req.to_dict())
        return LspDeclarationFileResponse.from_dict(data)

    def run_multi_attempt(self, req: LspMultiAttemptRequest) -> LspMultiAttemptResponse:
        data = self._post("/lsp/multi_attempt", req.to_dict())
        return LspMultiAttemptResponse.from_dict(data)

    def run_snippet(self, req: LspRunSnippetRequest) -> LspRunSnippetResponse:
        data = self._post("/lsp/run_snippet", req.to_dict())
        return LspRunSnippetResponse.from_dict(data)

    def run_declaration_soundness(
        self,
        req: LspDeclarationSoundnessRequest,
    ) -> LspDeclarationSoundnessResponse:
        data = self._post("/lsp/declaration_soundness", req.to_dict())
        return LspDeclarationSoundnessResponse.from_dict(data)

    def run_declaration_soundness_batch(
        self,
        req: LspDeclarationSoundnessBatchRequest,
    ) -> LspDeclarationSoundnessBatchResponse:
        data = self._post("/lsp/declaration_soundness_batch", req.to_dict())
        return LspDeclarationSoundnessBatchResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["LspAssistHttpClient"]
