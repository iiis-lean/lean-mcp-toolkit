"""Dynamic CLI tree built from visible tool aliases."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cli_catalog import ToolMeta


def alias_to_tokens(alias: str) -> tuple[str, ...]:
    text = str(alias).strip()
    if not text:
        return tuple()
    return tuple(part.strip().replace("_", "-") for part in text.split(".") if part.strip())


@dataclass(slots=True)
class ToolCommandNode:
    token: str
    children: dict[str, "ToolCommandNode"] = field(default_factory=dict)
    tools_by_alias: dict[str, ToolMeta] = field(default_factory=dict)

    def add_alias(self, alias: str, tool: ToolMeta) -> None:
        tokens = alias_to_tokens(alias)
        node = self
        for token in tokens:
            child = node.children.get(token)
            if child is None:
                child = ToolCommandNode(token=token)
                node.children[token] = child
            node = child
        node.tools_by_alias[alias] = tool

    def sorted_children(self) -> list["ToolCommandNode"]:
        return [self.children[key] for key in sorted(self.children.keys())]


@dataclass(slots=True, frozen=True)
class ToolResolution:
    tool: ToolMeta
    alias: str
    node: ToolCommandNode
    consumed_count: int
    consumed_tokens: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PartialResolution:
    node: ToolCommandNode
    consumed_count: int
    consumed_tokens: tuple[str, ...]


def build_tool_tree(tools: tuple[ToolMeta, ...]) -> ToolCommandNode:
    root = ToolCommandNode(token="")
    for tool in tools:
        for alias in tool.visible_aliases():
            root.add_alias(alias, tool)
    return root


def resolve_alias_path(root: ToolCommandNode, command_tokens: list[str]) -> PartialResolution:
    node = root
    consumed: list[str] = []
    for token in command_tokens:
        child = node.children.get(token)
        if child is None:
            break
        consumed.append(token)
        node = child
    return PartialResolution(
        node=node,
        consumed_count=len(consumed),
        consumed_tokens=tuple(consumed),
    )


def resolve_tool(root: ToolCommandNode, command_tokens: list[str]) -> ToolResolution | None:
    node = root
    consumed: list[str] = []
    best: ToolResolution | None = None
    for token in command_tokens:
        child = node.children.get(token)
        if child is None:
            break
        consumed.append(token)
        node = child
        if node.tools_by_alias:
            alias = sorted(node.tools_by_alias.keys())[0]
            best = ToolResolution(
                tool=node.tools_by_alias[alias],
                alias=alias,
                node=node,
                consumed_count=len(consumed),
                consumed_tokens=tuple(consumed),
            )
    return best


def subtree_lines(node: ToolCommandNode, *, indent: int = 0) -> list[str]:
    lines: list[str] = []
    prefix = "  " * max(indent, 0)
    if indent > 0 and node.token:
        lines.append(f"{prefix}{node.token}")
    for child in node.sorted_children():
        lines.extend(subtree_lines(child, indent=indent + 1))
    return lines
