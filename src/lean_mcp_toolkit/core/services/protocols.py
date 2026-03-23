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
    FileRequest,
    FileResponse,
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
from ...contracts.lsp_assist import (
    LspCompletionsRequest,
    LspCompletionsResponse,
    LspDeclarationFileRequest,
    LspDeclarationFileResponse,
    LspMultiAttemptRequest,
    LspMultiAttemptResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    LspTheoremSoundnessRequest,
    LspTheoremSoundnessResponse,
)
from ...contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavFileOutlineResponse,
    MathlibNavReadRequest,
    MathlibNavReadResponse,
    MathlibNavTreeRequest,
    MathlibNavTreeResponse,
)
from ...contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclFindResponse,
    MathlibDeclGetRequest,
    MathlibDeclGetResponse,
)
from ...contracts.search_nav import (
    LocalDeclFindRequest,
    LocalDeclFindResponse,
    LocalImportFindRequest,
    LocalImportFindResponse,
    LocalRefsFindRequest,
    LocalRefsFindResponse,
    LocalScopeFindRequest,
    LocalScopeFindResponse,
    LocalTextFindRequest,
    LocalTextFindResponse,
    RepoNavFileOutlineRequest,
    RepoNavFileOutlineResponse,
    RepoNavReadRequest,
    RepoNavReadResponse,
    RepoNavTreeRequest,
    RepoNavTreeResponse,
)


class DiagnosticsService(Protocol):
    """Service API expected by HTTP/MCP adapters."""

    def run_build(self, req: BuildRequest) -> BuildResponse:
        ...

    def run_file(self, req: FileRequest) -> FileResponse:
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


class LspAssistService(Protocol):
    """LSP-assist service API expected by HTTP/MCP adapters."""

    def run_completions(self, req: LspCompletionsRequest) -> LspCompletionsResponse:
        ...

    def run_declaration_file(
        self,
        req: LspDeclarationFileRequest,
    ) -> LspDeclarationFileResponse:
        ...

    def run_multi_attempt(self, req: LspMultiAttemptRequest) -> LspMultiAttemptResponse:
        ...

    def run_snippet(self, req: LspRunSnippetRequest) -> LspRunSnippetResponse:
        ...

    def run_theorem_soundness(
        self,
        req: LspTheoremSoundnessRequest,
    ) -> LspTheoremSoundnessResponse:
        ...


class SearchCoreService(Protocol):
    """Search-core service API expected by HTTP/MCP adapters."""

    def run_mathlib_decl_find(
        self,
        req: MathlibDeclFindRequest,
    ) -> MathlibDeclFindResponse:
        ...

    def run_mathlib_decl_get(self, req: MathlibDeclGetRequest) -> MathlibDeclGetResponse:
        ...


class MathlibNavService(Protocol):
    """Mathlib-nav service API expected by HTTP/MCP adapters."""

    def run_mathlib_nav_tree(self, req: MathlibNavTreeRequest) -> MathlibNavTreeResponse:
        ...

    def run_mathlib_nav_file_outline(
        self,
        req: MathlibNavFileOutlineRequest,
    ) -> MathlibNavFileOutlineResponse:
        ...

    def run_mathlib_nav_read(self, req: MathlibNavReadRequest) -> MathlibNavReadResponse:
        ...


class SearchNavService(Protocol):
    """Search-nav service API expected by HTTP/MCP adapters."""

    def run_repo_nav_tree(self, req: RepoNavTreeRequest) -> RepoNavTreeResponse:
        ...

    def run_repo_nav_file_outline(
        self,
        req: RepoNavFileOutlineRequest,
    ) -> RepoNavFileOutlineResponse:
        ...

    def run_repo_nav_read(self, req: RepoNavReadRequest) -> RepoNavReadResponse:
        ...

    def run_local_decl_find(self, req: LocalDeclFindRequest) -> LocalDeclFindResponse:
        ...

    def run_local_import_find(self, req: LocalImportFindRequest) -> LocalImportFindResponse:
        ...

    def run_local_scope_find(self, req: LocalScopeFindRequest) -> LocalScopeFindResponse:
        ...

    def run_local_text_find(self, req: LocalTextFindRequest) -> LocalTextFindResponse:
        ...

    def run_local_refs_find(self, req: LocalRefsFindRequest) -> LocalRefsFindResponse:
        ...
