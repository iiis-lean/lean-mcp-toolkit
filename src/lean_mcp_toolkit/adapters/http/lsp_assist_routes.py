"""HTTP-adapter handlers for lsp_assist tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_assist import (
    LspCompletionsRequest,
    LspCompiledDeclarationBatchRequest,
    LspDeclarationSoundnessBatchRequest,
    LspDeclarationSoundnessRequest,
    LspDeclarationFileRequest,
    LspMultiAttemptRequest,
)
from ...core.services import LspAssistService


def handle_lsp_completions(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspCompletionsRequest.from_dict(payload)
    resp = service.run_completions(req)
    return resp


def handle_lsp_declaration_file(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspDeclarationFileRequest.from_dict(payload)
    resp = service.run_declaration_file(req)
    return resp


def handle_lsp_multi_attempt(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspMultiAttemptRequest.from_dict(payload)
    resp = service.run_multi_attempt(req)
    return resp


def handle_lsp_declaration_soundness(service: LspAssistService, payload: JsonDict) -> JsonDict:
    req = LspDeclarationSoundnessRequest.from_dict(payload)
    resp = service.run_declaration_soundness(req)
    return resp


def handle_lsp_declaration_soundness_batch(
    service: LspAssistService,
    payload: JsonDict,
) -> JsonDict:
    req = LspDeclarationSoundnessBatchRequest.from_dict(payload)
    resp = service.run_declaration_soundness_batch(req)
    return resp


def handle_lsp_compiled_declaration_batch(
    service: LspAssistService,
    payload: JsonDict,
) -> JsonDict:
    req = LspCompiledDeclarationBatchRequest.from_dict(payload)
    resp = service.run_compiled_declaration_batch(req)
    return resp
