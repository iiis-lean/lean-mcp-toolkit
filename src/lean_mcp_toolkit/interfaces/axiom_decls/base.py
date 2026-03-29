"""Unified interface for direct axiom declaration checks.

This interface covers only direct source-level risks:
- top-level ``axiom`` / ``constant`` / ``opaque`` declarations (as configured)
- alias/export surfaces detected from source text

It intentionally does *not* cover transitive axiom usage. Usage auditing
remains in ``groups.diagnostics`` and still uses the existing probe-based
``#print axioms`` pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ...contracts.diagnostics import AxiomDeclaredItem


@dataclass(slots=True, frozen=True)
class AxiomDeclsInterfaceRequest:
    """Input for direct declaration-risk scanning."""

    project_root: Path
    module_dot: str
    allowed_kinds: tuple[str, ...]
    include_content: bool
    context_lines: int


@dataclass(slots=True, frozen=True)
class AxiomDeclsInterfaceResponse:
    """Normalized output for direct declaration-risk scanning.

    Field semantics:
    - ``declared_axioms``: direct risky declarations found in the current
      module. These are source-local items, not transitive dependencies.
    - ``alias_exports``: names exported via ``alias ... := ...`` syntax. This
      is a source-surface signal used later by higher-level diagnostics.
    """

    success: bool
    error_message: str | None = None
    declared_axioms: tuple[AxiomDeclaredItem, ...] = field(default_factory=tuple)
    alias_exports: tuple[str, ...] = field(default_factory=tuple)


class AxiomDeclsInterfaceBackend(Protocol):
    """Backend protocol for direct declaration-risk scanning."""

    backend_name: str

    def run(self, req: AxiomDeclsInterfaceRequest) -> AxiomDeclsInterfaceResponse:
        ...


__all__ = [
    "AxiomDeclsInterfaceBackend",
    "AxiomDeclsInterfaceRequest",
    "AxiomDeclsInterfaceResponse",
]
