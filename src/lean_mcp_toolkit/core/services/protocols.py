"""Service-layer protocols for adapter decoupling."""

from __future__ import annotations

from typing import Protocol

from ...contracts.diagnostics import BuildRequest, BuildResponse, LintRequest, LintResponse, NoSorryResult


class DiagnosticsService(Protocol):
    """Service API expected by HTTP/MCP adapters."""

    def run_build(self, req: BuildRequest) -> BuildResponse:
        ...

    def run_lint(self, req: LintRequest) -> LintResponse:
        ...

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        ...
