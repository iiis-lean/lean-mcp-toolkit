"""Shared command handling for remote CLI and local shell."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import shlex
from typing import Any, Sequence, TextIO

from .cli_catalog import ToolCatalog, ToolMeta
from .cli_config_store import CliConfigStore
from .cli_invoker import ToolInvoker
from .cli_output import render_root_help, render_tool_list_tree, write_error, write_json
from .cli_parser import build_tool_parser
from .cli_payload import namespace_to_payload
from .cli_tree import build_tool_tree, resolve_alias_path, resolve_tool


def execute_cli_tokens(
    argv: Sequence[str],
    *,
    prog: str,
    catalog: ToolCatalog,
    invoker: ToolInvoker | None,
    stdout: TextIO,
    stderr: TextIO,
    enable_config_commands: bool = False,
    config_store: CliConfigStore | None = None,
    remote: bool = True,
) -> int:
    tokens = [str(item) for item in argv if str(item).strip()]
    if not tokens or tokens[0] in {"help", "-h", "--help", "?"}:
        help_text = render_root_help(prog=prog, remote=remote)
        stdout.write(help_text)
        if not help_text.endswith("\n"):
            stdout.write("\n")
        return 0

    if tokens[0] == "tools":
        return _handle_tools(
            tokens[1:],
            catalog=catalog,
            stdout=stdout,
            stderr=stderr,
        )
    if tokens[0] == "config":
        if not enable_config_commands or config_store is None:
            write_error("config command is not available in this mode", stream=stderr)
            return 2
        return _handle_config(tokens[1:], config_store=config_store, stdout=stdout, stderr=stderr)

    if invoker is None:
        write_error("tool invocation is not available in this mode", stream=stderr)
        return 2
    return _handle_tool_command(
        tokens,
        prog=prog,
        catalog=catalog,
        invoker=invoker,
        stdout=stdout,
        stderr=stderr,
    )


def execute_cli_line(
    line: str,
    *,
    prog: str,
    catalog: ToolCatalog,
    invoker: ToolInvoker | None,
    stdout: TextIO,
    stderr: TextIO,
    enable_config_commands: bool = False,
    config_store: CliConfigStore | None = None,
    remote: bool = True,
) -> int:
    tokens = shlex.split(line)
    return execute_cli_tokens(
        tokens,
        prog=prog,
        catalog=catalog,
        invoker=invoker,
        stdout=stdout,
        stderr=stderr,
        enable_config_commands=enable_config_commands,
        config_store=config_store,
        remote=remote,
    )


def _handle_tools(
    argv: Sequence[str],
    *,
    catalog: ToolCatalog,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    compact = False
    json_mode = False
    for token in argv:
        if token == "--json":
            json_mode = True
        elif token == "--compact":
            compact = True
        elif token in {"-h", "--help"}:
            stdout.write("usage: tools [--json] [--compact]\n")
            return 0
        else:
            write_error(f"unknown tools argument: {token}", stream=stderr)
            return 2

    tools = catalog.list_tools()
    if json_mode:
        write_json([_tool_to_dict(tool) for tool in tools], stream=stdout, compact=compact)
        return 0

    tree = build_tool_tree(tools)
    alias_map = {
        alias: tool
        for tool in tools
        for alias in tool.visible_aliases()
    }
    stdout.write(render_tool_list_tree(tree, tool_by_alias=alias_map))
    return 0


def _handle_config(
    argv: Sequence[str],
    *,
    config_store: CliConfigStore,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        stdout.write("usage: config show | config set <key> <value>\n")
        return 0
    if argv[0] == "show":
        write_json(asdict(config_store.load()), stream=stdout)
        return 0
    if argv[0] == "set":
        if len(argv) != 3:
            write_error("usage: config set <key> <value>", stream=stderr)
            return 2
        try:
            cfg = config_store.set_value(argv[1], argv[2])
        except Exception as exc:
            write_error(str(exc), stream=stderr)
            return 2
        write_json(asdict(cfg), stream=stdout)
        return 0
    write_error(f"unknown config subcommand: {argv[0]}", stream=stderr)
    return 2


def _handle_tool_command(
    argv: Sequence[str],
    *,
    prog: str,
    catalog: ToolCatalog,
    invoker: ToolInvoker,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    tools = catalog.list_tools()
    tree = build_tool_tree(tools)
    split_idx = next((i for i, tok in enumerate(argv) if tok.startswith("-")), len(argv))
    command_tokens = list(argv[:split_idx])
    option_tokens = list(argv[split_idx:])

    resolution = resolve_tool(tree, command_tokens)
    if resolution is None or resolution.consumed_count != len(command_tokens):
        partial = resolve_alias_path(tree, command_tokens)
        if option_tokens and any(tok in {"-h", "--help"} for tok in option_tokens):
            lines = ["available commands:"]
            for child in partial.node.sorted_children():
                lines.append(f"  {child.token}")
            stdout.write("\n".join(lines) + "\n")
            return 0
        write_error(
            f"unknown tool path: {' '.join(command_tokens)}",
            stream=stderr,
        )
        return 2

    tool = resolution.tool
    matched_path = " ".join(resolution.consumed_tokens)
    parser = build_tool_parser(prog=f"{prog} {matched_path}", tool=tool)
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            ns = parser.parse_args(option_tokens)
    except SystemExit as exc:
        return int(exc.code or 0)

    payload = namespace_to_payload(ns, tool)
    try:
        result = invoker.invoke(tool.api_path, payload)
    except Exception as exc:
        write_error(str(exc), stream=stderr)
        return 1
    write_json(result, stream=stdout, compact=bool(getattr(ns, "compact", False)))
    return 0


def _tool_to_dict(tool: ToolMeta) -> dict[str, Any]:
    return {
        "group_name": tool.group_name,
        "canonical_name": tool.canonical_name,
        "raw_name": tool.raw_name,
        "aliases": list(tool.aliases),
        "api_path": tool.api_path,
        "description": tool.description,
        "api_description": tool.api_description,
        "mcp_description": tool.mcp_description,
        "params": [
            {
                "name": p.name,
                "type": p.type_hint,
                "description": p.description,
                "required": p.required,
                "default": p.default_value,
            }
            for p in tool.params
        ],
        "returns": [_return_to_dict(item) for item in tool.returns],
    }


def _return_to_dict(item: Any) -> dict[str, Any]:
    return {
        "field_path": item.field_path,
        "type": item.type_hint,
        "description": item.description,
        "children": [_return_to_dict(child) for child in item.children],
    }
