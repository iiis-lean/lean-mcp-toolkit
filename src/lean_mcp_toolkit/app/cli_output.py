"""Output rendering helpers for CLI entrypoints."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .cli_catalog import ToolMeta
from .cli_tree import ToolCommandNode


def write_json(data: Any, *, stream: TextIO | None = None, compact: bool = False) -> None:
    target = stream or sys.stdout
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    target.write(text)
    if not text.endswith("\n"):
        target.write("\n")


def write_error(message: str, *, stream: TextIO | None = None) -> None:
    target = stream or sys.stderr
    target.write(str(message).rstrip() + "\n")


def render_tool_list_tree(root: ToolCommandNode, *, tool_by_alias: dict[str, ToolMeta]) -> str:
    lines: list[str] = []

    def _visit(node: ToolCommandNode, indent: int) -> None:
        if node.token:
            lines.append(f"{'  ' * indent}{node.token}")
        for alias, tool in sorted(node.tools_by_alias.items()):
            alias_parts = alias.split(".")
            label = alias_parts[-1].replace("_", "-")
            desc = tool.description or tool.canonical_name
            lines.append(f"{'  ' * (indent + 1)}{label} : {desc}")
        for child in node.sorted_children():
            _visit(child, indent + (1 if node.token else 0))

    for child in root.sorted_children():
        _visit(child, 0)
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def render_root_help(*, prog: str, remote: bool) -> str:
    lines = [
        f"usage: {prog} [--base-url URL] <command> [<args>...]"
        if remote
        else f"usage: {prog} <command> [<args>...]",
        "",
        "Commands:",
        "  tools            List tools exposed by the current toolkit server/catalog.",
        "  config           Show or update user CLI defaults." if remote else "  help             Show help.",
        "  <tool path>      Invoke a tool using its visible alias path.",
        "",
        "Use `<tool path> --help` to see parameter help for a tool.",
    ]
    return "\n".join(lines)
