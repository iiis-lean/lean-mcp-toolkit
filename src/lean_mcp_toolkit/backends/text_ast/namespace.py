"""Namespace helpers for text AST parsing."""

from __future__ import annotations


def qualify_name(*, namespace_stack: tuple[str, ...], raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        return name
    if name.startswith("_root_."):
        return name
    if not namespace_stack:
        return name
    namespace_prefix = ".".join(namespace_stack)
    root_prefix = f"{namespace_stack[0]}."
    if name == namespace_prefix or name.startswith(f"{namespace_prefix}."):
        return name
    if name.startswith(root_prefix):
        return name
    return ".".join([*namespace_stack, name])


__all__ = ["qualify_name"]
