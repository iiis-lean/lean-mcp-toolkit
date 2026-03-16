from dataclasses import dataclass

from lean_mcp_toolkit.app import ToolkitHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeDiagnosticsClient:
    def run_build(self, req):
        _ = req
        class _Resp:
            def to_dict(self):
                return {"ok": True, "tool": "build"}
        return _Resp()

    def run_lint(self, req):
        _ = req
        class _Resp:
            def to_dict(self):
                return {"ok": True, "tool": "lint"}
        return _Resp()

    def run_lint_no_sorry(self, req):
        _ = req
        class _Resp:
            def to_dict(self):
                return {"ok": True, "tool": "no_sorry"}
        return _Resp()



def test_toolkit_http_client_dispatch() -> None:
    client = ToolkitHttpClient(diagnostics=_FakeDiagnosticsClient())
    assert client.dispatch_api("diagnostics.build", {})["tool"] == "build"
    assert client.dispatch_api("/diagnostics/lint", {})["tool"] == "lint"
    assert client.dispatch_api("diagnostics.lint.no_sorry", {})["tool"] == "no_sorry"



def test_toolkit_http_client_factory() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = ToolkitHttpClient.from_http_config(cfg)
    assert client.diagnostics.http_config.base_url == "http://127.0.0.1:18080"
