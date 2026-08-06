from dataclasses import dataclass

from lean_mcp_toolkit.contracts.lsp_assist import (
    LspCompletionsRequest,
    LspDeclarationSoundnessBatchRequest,
    LspDeclarationSoundnessRequest,
    LspDeclarationFileRequest,
    LspMultiAttemptRequest,
    LspRunSnippetRequest,
)
from lean_mcp_toolkit.groups.lsp_assist.client_http import LspAssistHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        _ = payload
        if path == "/lsp/completions":
            return {"success": True, "items": [{"label": "foo", "kind": "function"}], "count": 1}
        if path == "/lsp/declaration_file":
            return {"success": True, "target_file_path": "/tmp/A/B.lean"}
        if path == "/lsp/multi_attempt":
            return {"success": True, "items": [], "count": 0, "any_success": False}
        if path == "/lsp/run_snippet":
            return {
                "success": True,
                "diagnostics": [],
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            }
        if path == "/lsp/declaration_soundness":
            return {
                "success": True,
                "module": "A.B",
                "declaration_name": "A.B.t",
                "axioms": ["Classical.choice"],
                "warnings": [],
                "axiom_count": 1,
                "warning_count": 0,
            }
        if path == "/lsp/declaration_soundness_batch":
            return {
                "success": True,
                "items": [
                    {
                        "success": True,
                        "module": "A.B",
                        "declaration_name": "A.B.t",
                        "axioms": [],
                        "warnings": [],
                    }
                ],
                "count": 1,
                "success_count": 1,
                "failure_count": 0,
            }
        raise AssertionError(f"unexpected path: {path}")


def test_lsp_assist_http_client_roundtrip() -> None:
    client = LspAssistHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=_FakeHttpJsonClient(),
    )

    comp = client.run_completions(
        LspCompletionsRequest.from_dict(
            {"file_path": "A/B.lean", "line": 1, "column": 1}
        )
    )
    assert comp.success is True
    assert comp.count == 1

    decl = client.run_declaration_file(
        LspDeclarationFileRequest.from_dict({"file_path": "A/B.lean", "symbol": "foo"})
    )
    assert decl.success is True
    assert decl.target_file_path == "/tmp/A/B.lean"

    multi = client.run_multi_attempt(
        LspMultiAttemptRequest.from_dict(
            {"file_path": "A/B.lean", "line": 1, "snippets": ["simp"]}
        )
    )
    assert multi.success is True

    snippet = client.run_snippet(LspRunSnippetRequest.from_dict({"code": "def x := 1"}))
    assert snippet.success is True

    soundness = client.run_declaration_soundness(
        LspDeclarationSoundnessRequest.from_dict(
            {
                "module": "A.B",
                "declaration_name": "A.B.t",
                "scan_source": False,
            }
        )
    )
    assert soundness.success is True
    assert soundness.axiom_count == 1

    batch = client.run_declaration_soundness_batch(
        LspDeclarationSoundnessBatchRequest.from_dict(
            {
                "declarations": [
                    {"module": "A.B", "declaration_name": "A.B.t"}
                ],
                "scan_source": False,
            }
        )
    )
    assert batch.success is True
    assert batch.items[0].declaration_name == "A.B.t"
