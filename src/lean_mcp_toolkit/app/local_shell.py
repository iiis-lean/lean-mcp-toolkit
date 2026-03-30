"""Interactive local shell for lean-mcp-toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import readline
import shlex
import sys

from .cli_catalog import LocalToolCatalog
from .cli_invoker import LocalToolInvoker
from .cli_shared import execute_cli_line, execute_cli_tokens
from .cli_tree import build_tool_tree, resolve_tool
from .toolkit_server import ToolkitServer


@dataclass(slots=True)
class ToolkitLocalShell:
    server: ToolkitServer
    prompt: str = "toolkit> "
    history_path: Path = Path.home() / ".cache" / "lean-mcp-toolkit" / "shell_history"

    def run(self) -> int:
        catalog = LocalToolCatalog(self.server)
        invoker = LocalToolInvoker(self.server)
        self._setup_readline(catalog)
        try:
            while True:
                try:
                    line = input(self.prompt)
                except EOFError:
                    sys.stdout.write("\n")
                    break
                text = line.strip()
                if not text:
                    continue
                if text in {"quit", "exit"}:
                    break
                if text in {"help", "?"}:
                    execute_cli_tokens(
                        ["--help"],
                        prog="shell",
                        catalog=catalog,
                        invoker=invoker,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        enable_config_commands=False,
                        remote=False,
                    )
                    continue
                execute_cli_line(
                    text,
                    prog="shell",
                    catalog=catalog,
                    invoker=invoker,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    enable_config_commands=False,
                    remote=False,
                )
        finally:
            self._save_history()
        return 0

    def _setup_readline(self, catalog: LocalToolCatalog) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if self.history_path.is_file():
            try:
                readline.read_history_file(str(self.history_path))
            except Exception:
                pass
        readline.set_history_length(1000)
        readline.parse_and_bind("tab: complete")
        completer = _ShellCompleter(catalog)
        readline.set_completer(completer.complete)

    def _save_history(self) -> None:
        try:
            readline.write_history_file(str(self.history_path))
        except Exception:
            pass


class _ShellCompleter:
    def __init__(self, catalog: LocalToolCatalog):
        self.catalog = catalog

    def complete(self, text: str, state: int) -> str | None:
        candidates = self._candidates(text)
        if state < len(candidates):
            return candidates[state]
        return None

    def _candidates(self, text: str) -> list[str]:
        buf = readline.get_line_buffer()
        begidx = readline.get_begidx()
        prefix = buf[:begidx]
        try:
            prior = shlex.split(prefix)
        except Exception:
            prior = prefix.split()

        catalog_tools = self.catalog.list_tools()
        tree = build_tool_tree(catalog_tools)

        if text.startswith("-"):
            resolution = resolve_tool(tree, prior)
            if resolution is None:
                return []
            from .cli_parser import build_tool_parser

            parser = build_tool_parser(
                prog="shell " + " ".join(resolution.consumed_tokens),
                tool=resolution.tool,
            )
            options: list[str] = []
            for action in parser._actions:
                options.extend(action.option_strings)
            return sorted(opt for opt in options if opt.startswith(text))

        partial = prior + ([text] if text else [])
        node = tree
        for token in partial[:-1]:
            child = node.children.get(token)
            if child is None:
                return []
            node = child
        needle = partial[-1] if partial else ""
        static = ["tools", "help", "quit", "exit"]
        candidates = list(node.children.keys()) if prior else static + list(tree.children.keys())
        return sorted(item for item in set(candidates) if item.startswith(needle))
