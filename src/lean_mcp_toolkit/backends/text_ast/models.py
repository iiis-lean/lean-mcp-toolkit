"""Shared light-weight text AST models.

These models describe syntax-derived information only. They intentionally do
not claim elaboration-level accuracy, and callers must account for the fact
that some names/ranges/signatures can differ from Lean-backed extractors in
edge cases such as wrappers, aliases, and macro-heavy code.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TextAstPosition:
    """1-based source coordinate derived from plain-text parsing."""

    line: int
    column: int


@dataclass(slots=True, frozen=True)
class TextAstDeclaration:
    """Syntax-derived declaration summary.

    Field semantics:
    - ``name``: fully qualified declaration reconstructed from namespace state.
      This is the declaration introduced by the current file, not necessarily
      the referenced RHS name of an ``abbrev`` wrapper.
    - ``short_name``: unqualified declaration token from the header.
    - ``kind``: normalized declaration kind intended to align with Lean-backed
      outputs where practical.
    - ``signature``: normalized source-level signature/header fragment. It is
      not an elaborated type.
    - ``value`` / ``full_declaration``: exact source slices when available.
    - ``decl_*`` / ``doc_*`` positions: parser-derived 1-based coordinates.
    """

    name: str
    short_name: str
    kind: str
    signature: str | None = None
    value: str | None = None
    full_declaration: str | None = None
    docstring: str | None = None
    decl_start_pos: TextAstPosition | None = None
    decl_end_pos: TextAstPosition | None = None
    doc_start_pos: TextAstPosition | None = None
    doc_end_pos: TextAstPosition | None = None


@dataclass(slots=True, frozen=True)
class TextAstSorry:
    """Syntax-derived ``sorry``/``admit`` occurrence inside one source file."""

    pos: TextAstPosition
    end_pos: TextAstPosition | None
    line_text: str
    declaration_name: str | None = None


@dataclass(slots=True, frozen=True)
class TextAstCommandIssue:
    """One top-level command that the lightweight parser could not classify."""

    line: int
    column: int
    head: str
    source: str


@dataclass(slots=True, frozen=True)
class TextAstCoverage:
    """Source-command classification coverage, not Lean semantic coverage."""

    total_top_level_commands: int = 0
    classified_top_level_commands: int = 0
    unrecognized_commands: tuple[TextAstCommandIssue, ...] = field(default_factory=tuple)

    @property
    def classification_ratio(self) -> float:
        if self.total_top_level_commands == 0:
            return 1.0
        return self.classified_top_level_commands / self.total_top_level_commands


@dataclass(slots=True, frozen=True)
class ParsedLeanModule:
    """Parsed text/AST view of one Lean module."""

    declarations: tuple[TextAstDeclaration, ...] = field(default_factory=tuple)
    alias_exports: tuple[str, ...] = field(default_factory=tuple)
    coverage: TextAstCoverage = field(default_factory=TextAstCoverage)


__all__ = [
    "ParsedLeanModule",
    "TextAstCommandIssue",
    "TextAstCoverage",
    "TextAstDeclaration",
    "TextAstPosition",
    "TextAstSorry",
]
