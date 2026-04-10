"""Remote-first CLI entrypoint for toolkit tools."""

from __future__ import annotations

import argparse
import os
import sys
from typing import NoReturn

from ..transport.http import HttpConfig
from .cli_catalog import RemoteToolCatalog
from .cli_config_store import CliConfigStore, DEFAULT_API_PREFIX, DEFAULT_BASE_URL
from .cli_invoker import HttpToolInvoker
from .cli_shared import execute_cli_tokens
from .toolkit_client import ToolkitHttpClient


def main(argv: list[str] | None = None) -> NoReturn:
    args, rest = _parse_global_args(argv)
    store = CliConfigStore()
    cfg = store.load()
    base_url = (
        args.base_url
        or os.environ.get("LEAN_CLI_TOOLKIT_BASE_URL")
        or cfg.default_base_url
        or DEFAULT_BASE_URL
    )
    api_prefix = (
        args.api_prefix
        or os.environ.get("LEAN_CLI_TOOLKIT_API_PREFIX")
        or cfg.default_api_prefix
        or DEFAULT_API_PREFIX
    )
    tool_view = args.tool_view or os.environ.get("LEAN_CLI_TOOLKIT_TOOL_VIEW")
    http_config = HttpConfig(
        base_url=base_url,
        api_prefix=api_prefix,
        tool_view=tool_view,
        timeout_seconds=cfg.default_timeout_seconds,
    )
    catalog = RemoteToolCatalog.from_http_config(http_config)
    client = ToolkitHttpClient.from_http_config(http_config)
    invoker = HttpToolInvoker(client=client)
    code = execute_cli_tokens(
        rest,
        prog="lean-cli-toolkit",
        catalog=catalog,
        invoker=invoker,
        stdout=sys.stdout,
        stderr=sys.stderr,
        enable_config_commands=True,
        config_store=store,
        remote=True,
    )
    raise SystemExit(code)


def _parse_global_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--base-url")
    parser.add_argument("--api-prefix")
    parser.add_argument("--tool-view")
    parser.add_argument("-h", "--help", action="store_true")
    ns, rest = parser.parse_known_args(argv)
    if ns.help and not rest:
        rest = ["--help"]
    return ns, rest


if __name__ == "__main__":
    main()
