from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import sys

import pytest

from lean_mcp_toolkit.app import client_cli
from lean_mcp_toolkit.app.cli_catalog import ToolMeta


@dataclass(slots=True)
class _FakeCatalog:
    tools: tuple[ToolMeta, ...]

    def list_tools(self) -> tuple[ToolMeta, ...]:
        return self.tools


@dataclass(slots=True)
class _FakeClient:
    calls: list[tuple[str, dict]]

    def dispatch_api(self, route_path: str, payload: dict) -> dict:
        self.calls.append((route_path, payload))
        return {"route_path": route_path, "payload": payload}


def _tool() -> ToolMeta:
    return ToolMeta(
        group_name="diagnostics",
        canonical_name="diagnostics.build",
        raw_name="build",
        aliases=("diagnostics.build",),
        api_path="/diagnostics/build",
        description="build description",
        api_description="build api description",
        mcp_description="build mcp description",
        params=tuple(),
        returns=tuple(),
    )


def test_client_cli_uses_config_show_without_server(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text('default_base_url = "http://127.0.0.1:18888"\n', encoding="utf-8")
    store_cls = client_cli.CliConfigStore

    monkeypatch.setattr(
        client_cli,
        "CliConfigStore",
        lambda: store_cls(cfg_path),
    )

    out = StringIO()
    err = StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)

    with pytest.raises(SystemExit) as exc:
        client_cli.main(["config", "show"])

    assert exc.value.code == 0
    assert "18888" in out.getvalue()


def test_client_cli_invokes_remote_tool(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake_client = _FakeClient([])
    monkeypatch.setattr(
        client_cli.RemoteToolCatalog,
        "from_http_config",
        classmethod(lambda cls, http_config: _FakeCatalog((_tool(),))),
    )
    monkeypatch.setattr(
        client_cli.ToolkitHttpClient,
        "from_http_config",
        classmethod(lambda cls, http_config: fake_client),
    )
    cfg_path = tmp_path / "config.toml"
    store_cls = client_cli.CliConfigStore
    monkeypatch.setattr(
        client_cli,
        "CliConfigStore",
        lambda: store_cls(cfg_path),
    )

    out = StringIO()
    err = StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)

    with pytest.raises(SystemExit) as exc:
        client_cli.main(["diagnostics", "build"])

    assert exc.value.code == 0
    assert fake_client.calls == [("/diagnostics/build", {})]
    assert "/diagnostics/build" in out.getvalue()
