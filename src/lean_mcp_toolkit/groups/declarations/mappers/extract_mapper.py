"""Mapping from backend raw declaration objects to API contracts."""

from __future__ import annotations

from typing import Any

from ....contracts.declarations import DeclarationItem, DeclarationPosition


def map_raw_declarations_to_items(
    raw_declarations: tuple[Any, ...],
    *,
    source_lines: list[str] | None,
    include_value: bool,
) -> tuple[DeclarationItem, ...]:
    return tuple(
        _map_single_declaration(
            decl,
            source_lines=source_lines,
            include_value=include_value,
        )
        for decl in raw_declarations
    )


def _map_single_declaration(
    decl: Any,
    *,
    source_lines: list[str] | None,
    include_value: bool,
) -> DeclarationItem:
    decl_range = getattr(decl, "range", None)
    signature_obj = getattr(decl, "signature", None)
    signature_range = getattr(signature_obj, "range", None)
    value_obj = getattr(decl, "value", None)
    value_range = getattr(value_obj, "range", None)
    modifiers = getattr(decl, "modifiers", None)
    doc_string = getattr(modifiers, "doc_string", None)
    doc_range = getattr(doc_string, "range", None)

    signature = _slice_by_range(source_lines, signature_range)
    if signature is None:
        signature = _str_or_none(getattr(signature_obj, "pp", None))

    value = None
    if include_value:
        value = _slice_by_range(source_lines, value_range)
        if value is None:
            value = _str_or_none(getattr(value_obj, "pp", None))

    full_declaration = _slice_by_range(source_lines, decl_range)
    if full_declaration is None:
        full_declaration = _str_or_none(getattr(decl, "pp", None))

    docstring = _slice_by_range(source_lines, doc_range)
    if docstring is None:
        docstring = _str_or_none(getattr(doc_string, "content", None))

    return DeclarationItem(
        name=_str_or_none(getattr(decl, "full_name", None))
        or _str_or_none(getattr(decl, "name", None))
        or "",
        kind=_str_or_none(getattr(decl, "kind", None)),
        signature=signature,
        value=value,
        full_declaration=full_declaration,
        docstring=docstring,
        decl_start_pos=_position_from(getattr(decl_range, "start", None)),
        decl_end_pos=_position_from(getattr(decl_range, "finish", None)),
        doc_start_pos=_position_from(getattr(doc_range, "start", None)),
        doc_end_pos=_position_from(getattr(doc_range, "finish", None)),
    )


def _position_from(pos: Any) -> DeclarationPosition | None:
    if pos is None:
        return None
    line = getattr(pos, "line", None)
    column = getattr(pos, "column", None)
    if not isinstance(line, int) or not isinstance(column, int):
        return None
    return DeclarationPosition(line=line, column=column)


def _slice_by_range(source_lines: list[str] | None, range_obj: Any) -> str | None:
    if source_lines is None or range_obj is None:
        return None
    start = getattr(range_obj, "start", None)
    finish = getattr(range_obj, "finish", None)
    if start is None or finish is None:
        return None

    start_line = getattr(start, "line", None)
    start_col = getattr(start, "column", None)
    end_line = getattr(finish, "line", None)
    end_col = getattr(finish, "column", None)
    if not all(isinstance(v, int) for v in (start_line, start_col, end_line, end_col)):
        return None

    # LeanInteract ranges use 1-based lines and 0-based columns.
    sl = start_line - 1
    el = end_line - 1
    sc = start_col
    ec = end_col
    if sl < 0 or el < 0 or sc < 0 or ec < 0:
        return None
    if sl > el:
        return None
    if sl >= len(source_lines) or el >= len(source_lines):
        return None
    if sl == el:
        line = source_lines[sl]
        if sc > len(line) or ec > len(line) or sc > ec:
            return None
        return line[sc:ec]

    first_line = source_lines[sl]
    last_line = source_lines[el]
    if sc > len(first_line) or ec > len(last_line):
        return None
    parts = [first_line[sc:]]
    for idx in range(sl + 1, el):
        parts.append(source_lines[idx])
    parts.append(last_line[:ec])
    return "\n".join(parts)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None

