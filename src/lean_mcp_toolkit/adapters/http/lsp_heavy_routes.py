"""HTTP-adapter payload handlers for lsp_heavy tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspWidgetSourceRequest,
    LspWidgetsRequest,
)
from ...core.services import LspHeavyService


def handle_lsp_widgets(service: LspHeavyService, payload: JsonDict) -> JsonDict:
    req = LspWidgetsRequest.from_dict(payload)
    resp = service.run_widgets(req)
    return resp.to_dict()


def handle_lsp_widget_source(service: LspHeavyService, payload: JsonDict) -> JsonDict:
    req = LspWidgetSourceRequest.from_dict(payload)
    resp = service.run_widget_source(req)
    return resp.to_dict()


def handle_lsp_proof_profile(service: LspHeavyService, payload: JsonDict) -> JsonDict:
    req = LspProofProfileRequest.from_dict(payload)
    resp = service.run_proof_profile(req)
    return resp.to_dict()
