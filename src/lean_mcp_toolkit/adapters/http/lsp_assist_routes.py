"""HTTP-adapter handlers for lsp_assist tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_assist import (
    LspCompletionsRequest,
    LspDeclarationFileRequest,
    LspMultiAttemptRequest,
    LspTheoremSoundnessRequest,
)
from ...core.services import LspAssistService


def handle_lsp_completions(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspCompletionsRequest.from_dict(payload)
    resp = service.run_completions(req)
    return resp.to_dict()


def handle_lsp_declaration_file(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspDeclarationFileRequest.from_dict(payload)
    resp = service.run_declaration_file(req)
    return resp.to_dict()


def handle_lsp_multi_attempt(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspMultiAttemptRequest.from_dict(payload)
    resp = service.run_multi_attempt(req)
    return resp.to_dict()

def handle_lsp_theorem_soundness(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspTheoremSoundnessRequest.from_dict(payload)
    resp = service.run_theorem_soundness(req)
    return resp.to_dict()
