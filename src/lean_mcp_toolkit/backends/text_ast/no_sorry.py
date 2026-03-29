"""Text-based sorry scanning."""

from __future__ import annotations

import re

from .comments import mask_comments_and_strings
from .lexer import index_to_position, line_offsets
from .models import ParsedLeanModule, TextAstSorry

_SORRY_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_'])(?P<token>sorry|admit)(?![A-Za-z0-9_'])")


def collect_sorries(
    *,
    text: str,
    parsed_module: ParsedLeanModule,
) -> tuple[TextAstSorry, ...]:
    masked = mask_comments_and_strings(text)
    offsets = line_offsets(text)
    lines = text.splitlines()
    out: list[TextAstSorry] = []
    for match in _SORRY_TOKEN_RE.finditer(masked):
        start = index_to_position(offsets=offsets, index=match.start())
        end = index_to_position(offsets=offsets, index=max(match.start(), match.end() - 1))
        line_text = lines[start.line - 1] if 0 <= start.line - 1 < len(lines) else ""
        declaration_name = _find_enclosing_declaration(
            parsed_module=parsed_module,
            line=start.line,
            column=start.column,
        )
        out.append(
            TextAstSorry(
                pos=start,
                end_pos=end,
                line_text=line_text,
                declaration_name=declaration_name,
            )
        )
    return tuple(out)


def _find_enclosing_declaration(
    *,
    parsed_module: ParsedLeanModule,
    line: int,
    column: int,
) -> str | None:
    best_name: str | None = None
    best_span: int | None = None
    for decl in parsed_module.declarations:
        if decl.decl_start_pos is None or decl.decl_end_pos is None:
            continue
        start = decl.decl_start_pos
        end = decl.decl_end_pos
        if (line, column) < (start.line, start.column):
            continue
        if (line, column) > (end.line, end.column):
            continue
        span = (end.line - start.line) * 100000 + (end.column - start.column)
        if best_span is None or span < best_span:
            best_span = span
            best_name = decl.name
    return best_name


__all__ = ["collect_sorries"]
