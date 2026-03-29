"""Lightweight text/AST analysis helpers.

The parser and scanners in this package are toolkit-owned implementations, but
their scope and some structural ideas were informed by LongCat-Flash-Prover:
https://github.com/zhangjf-nlp/LongCat-Flash-Prover

This package is intentionally syntax-oriented rather than elaboration-oriented.
It is used to accelerate checks where text-level information is sufficient.
"""

from .axiom_decls import collect_axiom_declarations
from .declarations import parse_declarations
from .models import ParsedLeanModule, TextAstDeclaration, TextAstSorry
from .no_sorry import collect_sorries

__all__ = [
    "collect_axiom_declarations",
    "collect_sorries",
    "parse_declarations",
    "ParsedLeanModule",
    "TextAstDeclaration",
    "TextAstSorry",
]
