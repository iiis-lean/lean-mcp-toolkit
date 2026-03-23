from dataclasses import dataclass

from lean_mcp_toolkit.contracts.diagnostics import BuildRequest, FileRequest, LintRequest
from lean_mcp_toolkit.groups.diagnostics.client_http import DiagnosticsHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        if path == "/diagnostics/build":
            return {"success": True, "files": []}
        if path == "/diagnostics/file":
            return {
                "success": True,
                "file": "A.B",
                "items": [],
                "total_items": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "sorry_count": 0,
            }
        if path == "/diagnostics/lint":
            return {"success": True, "checks": []}
        if path == "/diagnostics/lint/no_sorry":
            return {"check_id": "no_sorry", "success": True, "message": "ok", "sorries": []}
        if path == "/diagnostics/lint/axiom_audit":
            return {
                "check_id": "axiom_audit",
                "success": True,
                "message": "ok",
                "declared_axioms": [],
                "usage_issues": [],
                "unresolved": [],
            }
        raise AssertionError(f"unexpected path: {path}")



def test_diagnostics_http_client_roundtrip() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = DiagnosticsHttpClient(http_config=cfg, http_client=_FakeHttpJsonClient())

    build = client.run_build(BuildRequest.from_dict({}))
    assert build.success is True

    file_diag = client.run_file(FileRequest.from_dict({"file_path": "A/B.lean"}))
    assert file_diag.success is True
    assert file_diag.file == "A.B"

    lint = client.run_lint(LintRequest.from_dict({}))
    assert lint.success is True

    no_sorry = client.run_lint_no_sorry(LintRequest.from_dict({}))
    assert no_sorry.check_id == "no_sorry"

    axiom_audit = client.run_lint_axiom_audit(LintRequest.from_dict({}))
    assert axiom_audit.check_id == "axiom_audit"
