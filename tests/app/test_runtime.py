from dataclasses import dataclass

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.diagnostics import (
    BuildRequest,
    BuildResponse,
    LintRequest,
    LintResponse,
    NoSorryResult,
)
from lean_mcp_toolkit.runtime import create_toolkit_runtime


@dataclass(slots=True)
class _FakeDiagnostics:
    def run_build(self, req: BuildRequest) -> BuildResponse:
        _ = req
        return BuildResponse(success=True, files=tuple())

    def run_lint(self, req: LintRequest) -> LintResponse:
        _ = req
        return LintResponse(success=True, checks=tuple())

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        _ = req
        return NoSorryResult(
            check_id="no_sorry",
            success=True,
            message="ok",
            sorries=tuple(),
        )


@dataclass(slots=True)
class _FakeToolkitHttpClient:
    diagnostics: _FakeDiagnostics

    def diagnostics_build(self, payload: dict) -> dict:
        return {"route": "build", "payload": payload}

    def diagnostics_lint(self, payload: dict) -> dict:
        return {"route": "lint", "payload": payload}

    def diagnostics_lint_no_sorry(self, payload: dict) -> dict:
        return {"route": "lint.no_sorry", "payload": payload}

    def dispatch_api(self, route_path: str, payload: dict) -> dict:
        return {"route_path": route_path, "payload": payload}


def test_create_toolkit_runtime_local(monkeypatch) -> None:
    fake_cfg = ToolkitConfig.from_dict({"server": {"default_project_root": "/tmp"}})
    fake_diagnostics = _FakeDiagnostics()

    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.load_toolkit_config",
        lambda config_path=None: fake_cfg,
    )
    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.create_diagnostics_service",
        lambda config: fake_diagnostics,
    )

    runtime = create_toolkit_runtime(mode="local", config_path="unused.toml")
    assert runtime.mode == "local"
    assert runtime.config == fake_cfg
    assert runtime.http_config is None
    assert runtime.diagnostics is fake_diagnostics

    build_out = runtime.diagnostics_build({})
    lint_out = runtime.diagnostics_lint({})
    no_sorry_out = runtime.diagnostics_lint_no_sorry({})

    assert build_out["success"] is True
    assert lint_out["success"] is True
    assert no_sorry_out["check_id"] == "no_sorry"
    assert runtime.dispatch_api("diagnostics.build", {})["success"] is True


def test_create_toolkit_runtime_http(monkeypatch) -> None:
    fake_cfg = ToolkitConfig.from_dict(
        {
            "server": {
                "host": "127.0.0.1",
                "port": 18888,
                "api_prefix": "/api/v1",
                "default_timeout_seconds": 12,
            }
        }
    )
    fake_diagnostics = _FakeDiagnostics()
    captured = {}

    def _fake_http_factory(*, http_config, config=None):
        captured["http_config"] = http_config
        captured["config"] = config
        return _FakeToolkitHttpClient(diagnostics=fake_diagnostics)

    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.load_toolkit_config",
        lambda config_path=None: fake_cfg,
    )
    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.create_toolkit_http_client",
        _fake_http_factory,
    )

    runtime = create_toolkit_runtime(
        mode="http",
        config_path="unused.toml",
        http_base_url_override="http://remote:19000",
    )

    assert runtime.mode == "http"
    assert runtime.config == fake_cfg
    assert runtime.diagnostics is fake_diagnostics
    assert runtime.http_config is not None
    assert runtime.http_config.base_url == "http://remote:19000"
    assert captured["http_config"].base_url == "http://remote:19000"
    assert captured["config"] == fake_cfg
    assert runtime.diagnostics_build({"k": 1})["route"] == "build"
    assert runtime.dispatch_api("/diagnostics/lint", {})["route_path"] == "/diagnostics/lint"
