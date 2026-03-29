"""Unified declarations interface models.

This layer gives ``groups.declarations`` one stable contract while allowing
multiple implementations underneath:

- ``lean_interact``: elaboration-backed extraction. Highest fidelity, heavier.
- ``text_ast``: syntax-derived extraction from source text. Much lighter, but
  still source-level and therefore only approximately aligned in some cases.
- ``simple_lean``: placeholder slot for a future lightweight Lean-native path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ...contracts.declarations import DeclarationItem


@dataclass(slots=True, frozen=True)
class DeclarationsInterfaceRequest:
    """Input for declaration extraction across backends."""

    project_root: Path
    target_dot: str
    timeout_seconds: int | None = None


@dataclass(slots=True, frozen=True)
class DeclarationsInterfaceResponse:
    """Normalized declaration extraction result.

    ``declarations`` uses the shared ``DeclarationItem`` contract, but backend
    semantics still matter:

    - ``name`` usually aligns across backends, but wrapper/abbrev files may
      expose the local wrapper name in ``text_ast`` where a Lean-backed backend
      can instead surface the referenced declaration.
    - ``kind`` is normalized for parity, but still originates from syntax in
      ``text_ast`` and from Lean-side extraction in ``lean_interact``.
    - ``signature`` in ``text_ast`` is reconstructed from source and normalized
      to resemble Lean-backed output; it is not an elaborated type.
    - ranges in ``text_ast`` are parser-derived exact source spans.
    """

    success: bool
    error_message: str | None = None
    declarations: tuple[DeclarationItem, ...] = field(default_factory=tuple)


class DeclarationsInterfaceBackend(Protocol):
    """Backend protocol for declaration extraction implementations."""

    backend_name: str

    def extract(self, req: DeclarationsInterfaceRequest) -> DeclarationsInterfaceResponse:
        ...

    def extract_batch(
        self,
        reqs: tuple[DeclarationsInterfaceRequest, ...],
    ) -> tuple[DeclarationsInterfaceResponse, ...]:
        ...


__all__ = [
    "DeclarationsInterfaceBackend",
    "DeclarationsInterfaceRequest",
    "DeclarationsInterfaceResponse",
]
