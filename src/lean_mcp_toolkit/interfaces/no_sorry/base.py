"""Unified interface for ``no_sorry`` implementations.

Supported implementations:
- ``lean``: the original diagnostics-driven implementation, with Lean command
  execution and semantic diagnostics.
- ``text_ast``: source-text scanning for ``sorry``/``admit`` that ignores
  comments and strings and reports declaration-local context.
"""

from __future__ import annotations

from typing import Protocol

from ...contracts.diagnostics import LintRequest, NoSorryResult


class NoSorryInterfaceBackend(Protocol):
    """Backend protocol for ``no_sorry`` implementations."""

    backend_name: str

    def run(self, req: LintRequest) -> NoSorryResult:
        ...


__all__ = ["NoSorryInterfaceBackend"]
