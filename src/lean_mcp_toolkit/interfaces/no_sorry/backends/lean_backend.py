"""Lean-backed ``no_sorry`` interface wrapper.

This preserves the historical diagnostics-based implementation and acts as the
semantic baseline when comparing with the lighter ``text_ast`` backend.
"""

from __future__ import annotations

from collections.abc import Callable

from ....contracts.diagnostics import LintRequest, NoSorryResult


class LeanNoSorryInterfaceBackend:
    """Thin adapter around the legacy Lean-backed ``no_sorry`` runner."""

    backend_name = "lean"

    def __init__(self, *, runner: Callable[[LintRequest], NoSorryResult]) -> None:
        self.runner = runner

    def run(self, req: LintRequest) -> NoSorryResult:
        return self.runner(req)


__all__ = ["LeanNoSorryInterfaceBackend"]
