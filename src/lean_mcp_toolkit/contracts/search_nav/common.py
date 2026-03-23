"""Common helpers/constants for search_nav contracts."""

from __future__ import annotations

from ..base import JsonDict, to_int, to_list_of_str

MATCH_MODES = {"exact", "prefix", "suffix"}
TEXT_MATCH_MODES = {"phrase", "word", "regex"}
IMPORT_DIRECTIONS = {"imports", "imported_by"}


def parse_match_mode(value: object, *, default: str = "prefix") -> str:
    raw = str(value or default).strip().lower()
    if raw in MATCH_MODES:
        return raw
    return default


def parse_text_match(value: object, *, default: str = "phrase") -> str:
    raw = str(value or default).strip().lower()
    if raw in TEXT_MATCH_MODES:
        return raw
    return default


def parse_import_direction(value: object, *, default: str = "imported_by") -> str:
    raw = str(value or default).strip().lower()
    if raw in IMPORT_DIRECTIONS:
        return raw
    return default


def parse_scopes(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    parsed = to_list_of_str(value)
    if parsed is None:
        return None
    return tuple(item for item in parsed if item)


def parse_limit(value: object, *, default: int | None = None) -> int | None:
    v = to_int(value, default=default)
    if v is None:
        return None
    return max(1, v)


def parse_context_lines(value: object, *, default: int | None = None) -> int | None:
    v = to_int(value, default=default)
    if v is None:
        return None
    return max(0, v)


def parse_int_or_none(value: object) -> int | None:
    return to_int(value, default=None)


def to_opt_str(data: JsonDict, key: str) -> str | None:
    return str(data[key]) if data.get(key) is not None else None


__all__ = [
    "MATCH_MODES",
    "TEXT_MATCH_MODES",
    "IMPORT_DIRECTIONS",
    "parse_match_mode",
    "parse_text_match",
    "parse_import_direction",
    "parse_scopes",
    "parse_limit",
    "parse_context_lines",
    "parse_int_or_none",
    "to_opt_str",
]
