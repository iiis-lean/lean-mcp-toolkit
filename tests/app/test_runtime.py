from dataclasses import dataclass

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.declarations import DeclarationExtractRequest, DeclarationExtractResponse
from lean_mcp_toolkit.contracts.diagnostics import (
    AxiomAuditResult,
    BuildRequest,
    BuildResponse,
    LintRequest,
    LintResponse,
    NoSorryResult,
)
from lean_mcp_toolkit.contracts.lsp_core import LspGoalRequest, LspGoalResponse
from lean_mcp_toolkit.contracts.mathlib_nav import MathlibNavTreeRequest, MathlibNavTreeResponse
from lean_mcp_toolkit.contracts.search_core import MathlibDeclFindRequest, MathlibDeclFindResponse
from lean_mcp_toolkit.contracts.search_nav import RepoNavTreeRequest, RepoNavTreeResponse
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

    def run_lint_axiom_audit(self, req: LintRequest) -> AxiomAuditResult:
        _ = req
        return AxiomAuditResult(
            check_id="axiom_audit",
            success=True,
            message="ok",
            declared_axioms=tuple(),
            usage_issues=tuple(),
            unresolved=tuple(),
        )


@dataclass(slots=True)
class _FakeDeclarations:
    def extract(self, req: DeclarationExtractRequest) -> DeclarationExtractResponse:
        _ = req
        return DeclarationExtractResponse(success=True, total_declarations=0, declarations=tuple())


@dataclass(slots=True)
class _FakeLspCore:
    def run_goal(self, req: LspGoalRequest) -> LspGoalResponse:
        _ = req
        return LspGoalResponse(success=True)


@dataclass(slots=True)
class _FakeSearchCore:
    def run_mathlib_decl_find(self, req: MathlibDeclFindRequest) -> MathlibDeclFindResponse:
        _ = req
        return MathlibDeclFindResponse(query="", count=0, processing_time_ms=None, results=tuple())


@dataclass(slots=True)
class _FakeMathlibNav:
    def run_mathlib_nav_tree(self, req: MathlibNavTreeRequest) -> MathlibNavTreeResponse:
        _ = req
        return MathlibNavTreeResponse(success=True, entries=tuple())


@dataclass(slots=True)
class _FakeSearchNav:
    def run_repo_nav_tree(self, req: RepoNavTreeRequest) -> RepoNavTreeResponse:
        _ = req
        return RepoNavTreeResponse(success=True, entries=tuple())


@dataclass(slots=True)
class _FakeToolkitHttpClient:
    diagnostics: _FakeDiagnostics
    declarations: _FakeDeclarations
    lsp_core: _FakeLspCore
    search_core: _FakeSearchCore
    mathlib_nav: _FakeMathlibNav
    search_nav: _FakeSearchNav

    def dispatch_api(self, route_path: str, payload: dict) -> dict:
        return {"route_path": route_path, "payload": payload}


@dataclass(slots=True)
class _FakeToolkitServer:
    diagnostics: _FakeDiagnostics
    declarations: _FakeDeclarations
    lsp_core: _FakeLspCore
    search_core: _FakeSearchCore
    mathlib_nav: _FakeMathlibNav
    search_nav: _FakeSearchNav

    def dispatch_api(self, route_path: str, payload: dict) -> dict:
        if route_path == "declarations.extract":
            return self.declarations.extract(DeclarationExtractRequest.from_dict(payload)).to_dict()
        if route_path == "diagnostics.build":
            return self.diagnostics.run_build(BuildRequest.from_dict(payload)).to_dict()
        if route_path == "diagnostics.lint":
            return self.diagnostics.run_lint(LintRequest.from_dict(payload)).to_dict()
        if route_path == "diagnostics.lint.no_sorry":
            return self.diagnostics.run_lint_no_sorry(LintRequest.from_dict(payload)).to_dict()
        raise KeyError(route_path)



def test_create_toolkit_runtime_local(monkeypatch) -> None:
    fake_cfg = ToolkitConfig.from_dict({"server": {"default_project_root": "/tmp"}})
    fake_diagnostics = _FakeDiagnostics()
    fake_declarations = _FakeDeclarations()
    fake_lsp_core = _FakeLspCore()
    fake_search_core = _FakeSearchCore()
    fake_mathlib_nav = _FakeMathlibNav()
    fake_search_nav = _FakeSearchNav()
    fake_server = _FakeToolkitServer(
        diagnostics=fake_diagnostics,
        declarations=fake_declarations,
        lsp_core=fake_lsp_core,
        search_core=fake_search_core,
        mathlib_nav=fake_mathlib_nav,
        search_nav=fake_search_nav,
    )

    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.load_toolkit_config",
        lambda config_path=None: fake_cfg,
    )
    monkeypatch.setattr(
        "lean_mcp_toolkit.runtime.create_local_toolkit_server",
        lambda config: fake_server,
    )

    runtime = create_toolkit_runtime(mode="local", config_path="unused.toml")
    assert runtime.mode == "local"
    assert runtime.config == fake_cfg
    assert runtime.http_config is None
    assert runtime.diagnostics is fake_diagnostics
    assert runtime.declarations is fake_declarations
    assert runtime.lsp_core is fake_lsp_core
    assert runtime.search_core is fake_search_core
    assert runtime.mathlib_nav is fake_mathlib_nav
    assert runtime.search_nav is fake_search_nav

    extract_out = runtime.dispatch_api("declarations.extract", {"target": "A.B"})
    build_out = runtime.dispatch_api("diagnostics.build", {})
    lint_out = runtime.dispatch_api("diagnostics.lint", {})
    no_sorry_out = runtime.dispatch_api("diagnostics.lint.no_sorry", {})

    assert extract_out["success"] is True
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
    fake_declarations = _FakeDeclarations()
    fake_lsp_core = _FakeLspCore()
    fake_search_core = _FakeSearchCore()
    fake_mathlib_nav = _FakeMathlibNav()
    fake_search_nav = _FakeSearchNav()
    captured = {}

    def _fake_http_factory(*, http_config, config=None):
        captured["http_config"] = http_config
        captured["config"] = config
        return _FakeToolkitHttpClient(
            diagnostics=fake_diagnostics,
            declarations=fake_declarations,
            lsp_core=fake_lsp_core,
            search_core=fake_search_core,
            mathlib_nav=fake_mathlib_nav,
            search_nav=fake_search_nav,
        )

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
    assert runtime.declarations is fake_declarations
    assert runtime.lsp_core is fake_lsp_core
    assert runtime.search_core is fake_search_core
    assert runtime.mathlib_nav is fake_mathlib_nav
    assert runtime.search_nav is fake_search_nav
    assert runtime.http_config is not None
    assert runtime.http_config.base_url == "http://remote:19000"
    assert captured["http_config"].base_url == "http://remote:19000"
    assert captured["config"] == fake_cfg
    assert runtime.dispatch_api("diagnostics.build", {"k": 1})["route_path"] == "diagnostics.build"
    assert runtime.dispatch_api("/diagnostics/lint", {})["route_path"] == "/diagnostics/lint"
