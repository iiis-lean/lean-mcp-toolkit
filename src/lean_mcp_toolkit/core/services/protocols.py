"""Service-layer protocols for adapter decoupling."""

from __future__ import annotations

from typing import Protocol

from ...contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationLocateRequest,
    DeclarationLocateResponse,
)
from ...contracts.diagnostics import (
    AxiomAuditResult,
    BuildRequest,
    BuildResponse,
    LintRequest,
    LintResponse,
    NoSorryResult,
)
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
from ...contracts.search_core import (
    LocalDeclSearchRequest,
    LocalDeclSearchResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
    MathlibDeclSearchRequest,
    MathlibDeclSearchResponse,
)


class DiagnosticsService(Protocol):
    """Service API expected by HTTP/MCP adapters."""

    def run_build(self, req: BuildRequest) -> BuildResponse:
        ...

    def run_lint(self, req: LintRequest) -> LintResponse:
        ...

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        ...

    def run_lint_axiom_audit(self, req: LintRequest) -> AxiomAuditResult:
        ...


class DeclarationsService(Protocol):
    """Declarations service API expected by HTTP/MCP adapters."""

    def extract(self, req: DeclarationExtractRequest) -> DeclarationExtractResponse:
        ...

    def locate(self, req: DeclarationLocateRequest) -> DeclarationLocateResponse:
        ...


class LspCoreService(Protocol):
    """LSP-core service API expected by HTTP/MCP adapters."""

    def run_file_outline(
        self,
        req: LspFileOutlineRequest,
    ) -> LspFileOutlineResponse | MarkdownResponse:
        ...

    def run_goal(self, req: LspGoalRequest) -> LspGoalResponse | MarkdownResponse:
        ...

    def run_term_goal(
        self,
        req: LspTermGoalRequest,
    ) -> LspTermGoalResponse | MarkdownResponse:
        ...

    def run_hover(self, req: LspHoverRequest) -> LspHoverResponse | MarkdownResponse:
        ...

    def run_code_actions(
        self,
        req: LspCodeActionsRequest,
    ) -> LspCodeActionsResponse | MarkdownResponse:
        ...


class SearchCoreService(Protocol):
    """Search-core service API expected by HTTP/MCP adapters."""

    def run_mathlib_decl_search(
        self,
        req: MathlibDeclSearchRequest,
    ) -> MathlibDeclSearchResponse:
        ...

    def run_mathlib_decl_get(self, req: MathlibDeclGetRequest) -> MathlibDeclGetResponse:
        ...

    def run_local_decl_search(self, req: LocalDeclSearchRequest) -> LocalDeclSearchResponse:
        ...
