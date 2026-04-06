"""HTTP-adapter handlers for lsp_core tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.lsp_core import (
    LspCodeActionsRequest,
    LspFileOutlineRequest,
    LspGoalRequest,
    LspHoverRequest,
    LspTermGoalRequest,
)
from ...contracts.lsp_assist import LspRunSnippetRequest
from ...core.services import LspCoreService


def handle_lsp_file_outline(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspFileOutlineRequest.from_dict(payload)
    resp = service.run_file_outline(req)
    return resp.to_dict()


def handle_lsp_goal(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspGoalRequest.from_dict(payload)
    resp = service.run_goal(req)
    return resp.to_dict()


def handle_lsp_term_goal(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspTermGoalRequest.from_dict(payload)
    resp = service.run_term_goal(req)
    return resp.to_dict()


def handle_lsp_hover(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspHoverRequest.from_dict(payload)
    resp = service.run_hover(req)
    return resp.to_dict()


def handle_lsp_code_actions(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspCodeActionsRequest.from_dict(payload)
    resp = service.run_code_actions(req)
    return resp.to_dict()


def handle_lsp_run_snippet(service: LspCoreService, payload: JsonDict) -> JsonDict:
    req = LspRunSnippetRequest.from_dict(payload)
    resp = service.run_snippet(req)
    return resp.to_dict()
