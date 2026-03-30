"""Dynamic parser helpers for tool subcommands."""

from __future__ import annotations

import argparse
import re
from typing import Any

from .cli_catalog import ToolMeta, ToolParamMeta

_LITERAL_PATTERN = re.compile(r'"([^"]+)"')


def build_tool_parser(*, prog: str, tool: ToolMeta) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=tool.preferred_help_text(),
    )
    for param in tool.params:
        _add_param_argument(parser, param)
    parser.add_argument(
        "--payload-file",
        dest="__payload_file",
        help="Load base payload from a JSON file.",
    )
    parser.add_argument(
        "--json",
        dest="__payload_json",
        help="Load base payload from an inline JSON object string.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON output.",
    )
    return parser


def _add_param_argument(parser: argparse.ArgumentParser, param: ToolParamMeta) -> None:
    option = f"--{param.name.replace('_', '-')}"
    kwargs: dict[str, Any] = {
        "dest": param.name,
        "help": _param_help(param),
    }
    required = bool(param.required)
    type_hint = param.type_hint

    if _is_bool_type(type_hint):
        if required:
            kwargs["required"] = True
            kwargs["type"] = _parse_bool
            kwargs["metavar"] = "BOOL"
            parser.add_argument(option, **kwargs)
            return
        kwargs["action"] = "store_true"
        kwargs["default"] = None
        parser.add_argument(option, **kwargs)
        parser.add_argument(
            f"--no-{param.name.replace('_', '-')}",
            dest=param.name,
            action="store_false",
            help=f"Set {param.name} to false.",
        )
        return

    if _is_list_like(type_hint):
        kwargs["action"] = "append"
        kwargs["required"] = required
        kwargs["type"] = str
        parser.add_argument(option, **kwargs)
        return

    choices = _extract_literal_choices(type_hint)
    if choices:
        kwargs["choices"] = choices
        kwargs["type"] = str
        kwargs["required"] = required
        parser.add_argument(option, **kwargs)
        return

    if _is_int_type(type_hint):
        kwargs["type"] = int
    elif _is_float_type(type_hint):
        kwargs["type"] = float
    else:
        kwargs["type"] = str
    kwargs["required"] = required
    parser.add_argument(option, **kwargs)


def _param_help(param: ToolParamMeta) -> str:
    text = param.description.strip()
    if param.default_value is not None:
        text += f" Default: {param.default_value}."
    return text


def _parse_bool(raw: str) -> bool:
    text = raw.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {raw}")


def _is_bool_type(type_hint: str) -> bool:
    return "bool" in type_hint


def _is_int_type(type_hint: str) -> bool:
    return "int" in type_hint and "float" not in type_hint


def _is_float_type(type_hint: str) -> bool:
    return "float" in type_hint


def _is_list_like(type_hint: str) -> bool:
    text = type_hint.replace(" ", "")
    return text.startswith("list[") or "list[" in text or "list[str]|str" in text


def _extract_literal_choices(type_hint: str) -> list[str]:
    choices = [item for item in _LITERAL_PATTERN.findall(type_hint) if item]
    return choices
