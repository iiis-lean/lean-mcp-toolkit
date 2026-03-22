"""lsp_core contracts."""

from .code_actions import CodeAction, CodeActionEdit, LspCodeActionsRequest, LspCodeActionsResponse
from .common import DiagnosticMessage, MarkdownResponse, OutlineEntry, normalize_response_format
from .file_outline import LspFileOutlineRequest, LspFileOutlineResponse
from .goal import LspGoalRequest, LspGoalResponse
from .hover import LspHoverRequest, LspHoverResponse
from .term_goal import LspTermGoalRequest, LspTermGoalResponse

__all__ = [
    "normalize_response_format",
    "MarkdownResponse",
    "DiagnosticMessage",
    "OutlineEntry",
    "LspFileOutlineRequest",
    "LspFileOutlineResponse",
    "LspGoalRequest",
    "LspGoalResponse",
    "LspTermGoalRequest",
    "LspTermGoalResponse",
    "LspHoverRequest",
    "LspHoverResponse",
    "LspCodeActionsRequest",
    "LspCodeActionsResponse",
    "CodeAction",
    "CodeActionEdit",
]
