"""Text-based direct axiom declaration scanning."""

from __future__ import annotations

from .models import ParsedLeanModule, TextAstDeclaration


def collect_axiom_declarations(
    *,
    parsed_module: ParsedLeanModule,
    allowed_kinds: set[str],
) -> tuple[TextAstDeclaration, ...]:
    return tuple(
        decl
        for decl in parsed_module.declarations
        if decl.kind.strip().lower() in allowed_kinds
    )


__all__ = ["collect_axiom_declarations"]
