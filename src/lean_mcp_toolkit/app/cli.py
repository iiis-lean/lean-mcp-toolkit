"""CLI entrypoint for server commands and local shell."""

from __future__ import annotations

import json
import sys
from typing import NoReturn

from ..config.cli import cli_args_to_overrides, parse_cli_args
from ..config.loader import load_toolkit_config
from .local_shell import ToolkitLocalShell
from .toolkit_server import ToolkitServer


def main(argv: list[str] | None = None) -> NoReturn:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    command = "serve"
    if raw_argv and raw_argv[0] in {"serve", "shell", "print-config"}:
        command = raw_argv.pop(0)

    args = parse_cli_args(raw_argv)
    overrides = cli_args_to_overrides(args)
    cfg = load_toolkit_config(config_path=args.config_path, cli_overrides=overrides)
    if args.print_config or command == "print-config":
        print(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(0)

    server = ToolkitServer.from_config(cfg)
    try:
        if command == "shell":
            shell = ToolkitLocalShell(server=server)
            raise SystemExit(shell.run())

        server.run()
        raise SystemExit(0)
    finally:
        try:
            server.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
