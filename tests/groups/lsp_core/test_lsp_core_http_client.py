from dataclasses import dataclass

from lean_mcp_toolkit.contracts.lsp_core import LspGoalRequest, LspRunSnippetRequest
from lean_mcp_toolkit.groups.lsp_core.client_http import LspCoreHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        if path == "/lsp/goal":
            return {
                "success": True,
                "line_context": "theorem t : True := by",
                "goals": ["⊢ True"],
            }
        if path == "/lsp/run_snippet":
            return {
                "success": True,
                "diagnostics": [],
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            }
        raise AssertionError(f"unexpected path: {path}")


def test_lsp_core_http_client_returns_structured_payloads() -> None:
    client = LspCoreHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=_FakeHttpJsonClient(),
    )

    structured = client.run_goal(LspGoalRequest.from_dict({"file_path": "A/B.lean", "line": 3}))
    assert structured.success is True
    assert structured.goals == ("⊢ True",)

    snippet = client.run_snippet(LspRunSnippetRequest.from_dict({"code": "def x := 1"}))
    assert snippet.success is True
