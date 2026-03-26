"""CLI entrypoint."""

from __future__ import annotations

import json
from typing import NoReturn

from ..config.cli import cli_args_to_overrides, parse_cli_args
from ..config.loader import load_toolkit_config
from .toolkit_server import ToolkitServer


def main() -> NoReturn:
    args = parse_cli_args()
    overrides = cli_args_to_overrides(args)
    cfg = load_toolkit_config(config_path=args.config_path, cli_overrides=overrides)
    if args.print_config:
        print(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(0)

    server = ToolkitServer.from_config(cfg)
    server.run()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
