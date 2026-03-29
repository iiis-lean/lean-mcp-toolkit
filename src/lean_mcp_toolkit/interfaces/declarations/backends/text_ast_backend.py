"""Declarations interface adapter for text/AST parsing.

This backend uses the lightweight parser in ``backends.text_ast``. It is
optimized for speed and for source-oriented workflows such as wrapper files,
Package/Summary surfaces, and declaration-driven lint helpers.
"""

from __future__ import annotations

from ....backends.lean.path import LeanPath
from ....backends.text_ast import parse_declarations
from ..base import DeclarationsInterfaceRequest, DeclarationsInterfaceResponse
from ..mappers import map_text_ast_declarations_to_items


class TextAstDeclarationsInterfaceBackend:
    """Adapt syntax-derived declarations to ``DeclarationsInterfaceResponse``.

    Differences from ``lean_interact`` that callers should know:
    - ``name`` is the declaration introduced by the current file as reconstructed
      from namespace state; wrapper/abbrev names can therefore differ from a
      Lean-backed extractor that reports the referenced RHS declaration.
    - ``signature`` is source-normalized rather than elaborated.
    - positions are parser-derived exact source ranges.
    """

    backend_name = "text_ast"

    def __init__(self, *, include_value: bool = False) -> None:
        self.include_value = include_value

    def extract(self, req: DeclarationsInterfaceRequest) -> DeclarationsInterfaceResponse:
        try:
            abs_file = (req.project_root / LeanPath.from_dot(req.target_dot).to_rel_file()).resolve()
            text = abs_file.read_text(encoding="utf-8")
            parsed = parse_declarations(text=text, module_dot=req.target_dot)
            items = map_text_ast_declarations_to_items(
                parsed.declarations,
                include_value=self.include_value,
            )
            return DeclarationsInterfaceResponse(
                success=True,
                error_message=None,
                declarations=items,
            )
        except Exception as exc:
            return DeclarationsInterfaceResponse(
                success=False,
                error_message=str(exc),
                declarations=tuple(),
            )

    def extract_batch(
        self,
        reqs: tuple[DeclarationsInterfaceRequest, ...],
    ) -> tuple[DeclarationsInterfaceResponse, ...]:
        return tuple(self.extract(req) for req in reqs)


__all__ = ["TextAstDeclarationsInterfaceBackend"]
