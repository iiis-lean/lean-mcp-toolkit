from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import sys

import pytest

from lean_mcp_toolkit.app import cli as app_cli


@dataclass(slots=True)
class _FakeServer:
    ran: bool = False
    closed: bool = False

    def run(self) -> None:
        self.ran = True

    def close(self) -> None:
        self.closed = True


@dataclass(slots=True)
class _FakeShell:
    server: _FakeServer
    code: int = 0

    def run(self) -> int:
        return self.code


def test_app_cli_default_mode_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_server = _FakeServer()
    monkeypatch.setattr(app_cli, "parse_cli_args", lambda argv=None: type("Ns", (), {"config_path": None, "print_config": False})())
    monkeypatch.setattr(app_cli, "cli_args_to_overrides", lambda args: {})
    monkeypatch.setattr(app_cli, "load_toolkit_config", lambda config_path=None, cli_overrides=None: object())
    monkeypatch.setattr(app_cli.ToolkitServer, "from_config", classmethod(lambda cls, cfg: fake_server))

    with pytest.raises(SystemExit) as exc:
        app_cli.main([])

    assert exc.value.code == 0
    assert fake_server.ran is True
    assert fake_server.closed is True


def test_app_cli_shell_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_server = _FakeServer()
    monkeypatch.setattr(app_cli, "parse_cli_args", lambda argv=None: type("Ns", (), {"config_path": None, "print_config": False})())
    monkeypatch.setattr(app_cli, "cli_args_to_overrides", lambda args: {})
    monkeypatch.setattr(app_cli, "load_toolkit_config", lambda config_path=None, cli_overrides=None: object())
    monkeypatch.setattr(app_cli.ToolkitServer, "from_config", classmethod(lambda cls, cfg: fake_server))
    monkeypatch.setattr(app_cli, "ToolkitLocalShell", lambda server: _FakeShell(server=server, code=7))

    with pytest.raises(SystemExit) as exc:
        app_cli.main(["shell"])

    assert exc.value.code == 7
    assert fake_server.closed is True


def test_app_cli_print_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_cli, "parse_cli_args", lambda argv=None: type("Ns", (), {"config_path": None, "print_config": False})())
    monkeypatch.setattr(app_cli, "cli_args_to_overrides", lambda args: {})
    monkeypatch.setattr(
        app_cli,
        "load_toolkit_config",
        lambda config_path=None, cli_overrides=None: type("Cfg", (), {"to_dict": lambda self: {"server": {"mode": "http"}}})(),
    )
    out = StringIO()
    monkeypatch.setattr(sys, "stdout", out)

    with pytest.raises(SystemExit) as exc:
        app_cli.main(["print-config"])

    assert exc.value.code == 0
    assert '"mode": "http"' in out.getvalue()
