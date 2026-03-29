"""Text/AST direct axiom declaration backend.

This backend scans only source-local declaration headers and alias syntax. It
does not attempt to infer transitive theorem dependencies; that remains the
responsibility of the probe-based usage audit.
"""

from __future__ import annotations

from ....backends.lean.path import LeanPath
from ....backends.text_ast import collect_axiom_declarations, parse_declarations
from ....contracts.diagnostics import AxiomDeclaredItem, Position
from ..base import AxiomDeclsInterfaceRequest, AxiomDeclsInterfaceResponse


class TextAstAxiomDeclsInterfaceBackend:
    """Run direct declaration/alias scanning via lightweight text/AST parsing.

    Differences versus ``lean``:
    - operates purely on source text and parser-derived declaration ranges;
    - returns exact local declarations introduced in the file;
    - keeps ``alias_exports`` as a direct source-surface signal for higher-level
      diagnostics orchestration.
    """

    backend_name = "text_ast"

    def run(self, req: AxiomDeclsInterfaceRequest) -> AxiomDeclsInterfaceResponse:
        try:
            abs_file = (req.project_root / LeanPath.from_dot(req.module_dot).to_rel_file()).resolve()
            text = abs_file.read_text(encoding="utf-8")
            parsed = parse_declarations(text=text, module_dot=req.module_dot)
            declared = collect_axiom_declarations(
                parsed_module=parsed,
                allowed_kinds={item.strip().lower() for item in req.allowed_kinds if item.strip()},
            )
            lines = text.splitlines()
            items: list[AxiomDeclaredItem] = []
            for decl in declared:
                content = None
                if req.include_content:
                    if decl.full_declaration:
                        content = decl.full_declaration
                    elif decl.decl_start_pos is not None and decl.decl_end_pos is not None:
                        start_idx = max(0, decl.decl_start_pos.line - 1 - max(0, req.context_lines))
                        end_idx = min(len(lines), decl.decl_end_pos.line + max(0, req.context_lines))
                        content = "\n".join(lines[start_idx:end_idx])
                items.append(
                    AxiomDeclaredItem(
                        fileName=req.module_dot,
                        declaration=decl.name,
                        kind=decl.kind,
                        pos=_map_pos(decl.decl_start_pos),
                        endPos=_map_pos(decl.decl_end_pos),
                        content=content,
                    )
                )
            return AxiomDeclsInterfaceResponse(
                success=True,
                error_message=None,
                declared_axioms=tuple(items),
                alias_exports=parsed.alias_exports,
            )
        except Exception as exc:
            return AxiomDeclsInterfaceResponse(
                success=False,
                error_message=str(exc),
                declared_axioms=tuple(),
                alias_exports=tuple(),
            )


def _map_pos(pos: object) -> Position | None:
    if pos is None:
        return None
    line = getattr(pos, "line", None)
    column = getattr(pos, "column", None)
    if not isinstance(line, int) or not isinstance(column, int):
        return None
    return Position(line=line, column=column)


__all__ = ["TextAstAxiomDeclsInterfaceBackend"]
