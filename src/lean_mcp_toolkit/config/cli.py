"""CLI argument parsing for configuration overrides."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any

from ..contracts.base import JsonDict
from .loader import apply_path_override


@dataclass(slots=True)
class ConfigCLIArgs:
    config_path: str | None = None
    mode: str | None = None
    host: str | None = None
    port: int | None = None
    project_root: str | None = None
    enable_groups: list[str] = field(default_factory=list)
    disable_groups: list[str] = field(default_factory=list)
    include_tools: list[str] = field(default_factory=list)
    exclude_tools: list[str] = field(default_factory=list)
    set_items: list[str] = field(default_factory=list)
    print_config: bool = False



def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="lean-mcp-toolkit configuration")
    parser.add_argument("--config", dest="config_path")
    parser.add_argument("--mode", choices=["mcp", "http", "unified"])
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--project-root", "--default-project-root", dest="project_root")
    parser.add_argument("--enable-group", action="append", default=[])
    parser.add_argument("--disable-group", action="append", default=[])
    parser.add_argument("--include-tool", action="append", default=[])
    parser.add_argument("--exclude-tool", action="append", default=[])
    parser.add_argument("--set", dest="set_items", action="append", default=[])
    parser.add_argument("--print-config", action="store_true")
    return parser



def parse_cli_args(argv: list[str] | None = None) -> ConfigCLIArgs:
    parser = build_arg_parser()
    ns = parser.parse_args(argv)
    return ConfigCLIArgs(
        config_path=ns.config_path,
        mode=ns.mode,
        host=ns.host,
        port=ns.port,
        project_root=ns.project_root,
        enable_groups=list(ns.enable_group or []),
        disable_groups=list(ns.disable_group or []),
        include_tools=list(ns.include_tool or []),
        exclude_tools=list(ns.exclude_tool or []),
        set_items=list(ns.set_items or []),
        print_config=bool(ns.print_config),
    )


def _coerce_set_value(raw: str) -> Any:
    text = raw.strip()
    lower = text.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        try:
            return int(text)
        except ValueError:
            pass
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return text


def cli_args_to_overrides(args: ConfigCLIArgs) -> JsonDict:
    data: JsonDict = {}

    if args.mode is not None:
        apply_path_override(data, "server.mode", args.mode)
    if args.host is not None:
        apply_path_override(data, "server.host", args.host)
    if args.port is not None:
        apply_path_override(data, "server.port", args.port)
    if args.project_root is not None:
        apply_path_override(data, "server.default_project_root", args.project_root)

    if args.enable_groups:
        apply_path_override(data, "groups.enabled_groups", args.enable_groups)
    if args.disable_groups:
        apply_path_override(data, "groups.disabled_groups", args.disable_groups)
    if args.include_tools:
        apply_path_override(data, "groups.include_tools", args.include_tools)
    if args.exclude_tools:
        apply_path_override(data, "groups.exclude_tools", args.exclude_tools)

    for set_item in args.set_items:
        if "=" not in set_item:
            continue
        path, raw_value = set_item.split("=", 1)
        path = path.strip()
        if not path:
            continue
        apply_path_override(data, path, _coerce_set_value(raw_value))

    return data
