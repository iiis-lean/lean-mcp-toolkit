"""Identifier scanning helpers."""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")


def collect_identifiers(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _IDENT_RE.finditer(text))


__all__ = ["collect_identifiers"]
