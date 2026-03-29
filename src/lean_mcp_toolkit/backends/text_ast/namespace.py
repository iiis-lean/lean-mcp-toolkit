"""Namespace helpers for text AST parsing."""

from __future__ import annotations


def qualify_name(*, namespace_stack: tuple[str, ...], raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        return name
    if name.startswith("_root_.") or "." in name:
        return name
    if not namespace_stack:
        return name
    return ".".join([*namespace_stack, name])


__all__ = ["qualify_name"]
