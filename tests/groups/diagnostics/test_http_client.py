from dataclasses import dataclass

from lean_mcp_toolkit.contracts.diagnostics import BuildRequest, LintRequest
from lean_mcp_toolkit.groups.diagnostics.client_http import DiagnosticsHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        if path == "/diagnostics/build":
            return {"success": True, "files": []}
        if path == "/diagnostics/lint":
            return {"success": True, "checks": []}
        if path == "/diagnostics/lint/no_sorry":
            return {"check_id": "no_sorry", "success": True, "message": "ok", "sorries": []}
        raise AssertionError(f"unexpected path: {path}")



def test_diagnostics_http_client_roundtrip() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = DiagnosticsHttpClient(http_config=cfg, http_client=_FakeHttpJsonClient())

    build = client.run_build(BuildRequest.from_dict({}))
    assert build.success is True

    lint = client.run_lint(LintRequest.from_dict({}))
    assert lint.success is True

    no_sorry = client.run_lint_no_sorry(LintRequest.from_dict({}))
    assert no_sorry.check_id == "no_sorry"
