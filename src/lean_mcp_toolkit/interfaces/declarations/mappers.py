"""Mappers for declarations interface backends.

Both mapper families target the same ``DeclarationItem`` schema, but their
inputs have different semantics:

- Lean-backed mappers receive elaboration-oriented declaration payloads.
- text/AST mappers receive syntax-derived declarations that were normalized to
  resemble Lean-backed outputs where practical.
"""

from __future__ import annotations

from ...contracts.declarations import DeclarationItem, DeclarationPosition
from ...groups.declarations.mappers import map_raw_declarations_to_items
from ...backends.text_ast.models import TextAstDeclaration


def map_text_ast_declarations_to_items(
    declarations: tuple[TextAstDeclaration, ...],
    *,
    include_value: bool,
) -> tuple[DeclarationItem, ...]:
    """Map syntax-derived declarations into the shared contract."""
    return tuple(
        DeclarationItem(
            name=decl.name,
            kind=decl.kind,
            signature=decl.signature,
            value=(decl.value if include_value else None),
            full_declaration=decl.full_declaration,
            docstring=decl.docstring,
            decl_start_pos=_map_pos(decl.decl_start_pos),
            decl_end_pos=_map_pos(decl.decl_end_pos),
            doc_start_pos=_map_pos(decl.doc_start_pos),
            doc_end_pos=_map_pos(decl.doc_end_pos),
        )
        for decl in declarations
    )


def map_lean_raw_declarations_to_items(
    raw_declarations: tuple[object, ...],
    *,
    source_lines: list[str] | None,
    include_value: bool,
) -> tuple[DeclarationItem, ...]:
    """Map Lean-backed raw declarations into the shared contract."""
    return map_raw_declarations_to_items(
        raw_declarations,
        source_lines=source_lines,
        include_value=include_value,
    )


def _map_pos(pos: object) -> DeclarationPosition | None:
    """Convert backend-specific position objects into contract positions."""
    if pos is None:
        return None
    line = getattr(pos, "line", None)
    column = getattr(pos, "column", None)
    if not isinstance(line, int) or not isinstance(column, int):
        return None
    return DeclarationPosition(line=line, column=column)


__all__ = [
    "map_lean_raw_declarations_to_items",
    "map_text_ast_declarations_to_items",
]
