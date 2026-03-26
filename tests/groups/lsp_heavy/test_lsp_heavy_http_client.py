from lean_mcp_toolkit.contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspWidgetSourceRequest,
    LspWidgetsRequest,
)
from lean_mcp_toolkit.groups.lsp_heavy.client_http import LspHeavyHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


class _FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post_json(self, path: str, payload: dict) -> dict:
        self.calls.append((path, payload))
        if path == "/lsp/widgets":
            return {"success": True, "widgets": [], "count": 0}
        if path == "/lsp/widget_source":
            return {
                "success": True,
                "javascript_hash": "abc",
                "source_text": "x",
                "raw_source": {},
            }
        if path == "/lsp/proof_profile":
            return {
                "success": True,
                "theorem_name": "t",
                "total_ms": 1.0,
                "lines": [],
                "count": 0,
                "categories": [],
                "category_count": 0,
            }
        raise AssertionError(path)


def test_lsp_heavy_http_client_roundtrip() -> None:
    http = _FakeHttpClient()
    client = LspHeavyHttpClient(
        http_config=HttpConfig(base_url="http://example.com"),
        http_client=http,
    )

    widgets = client.run_widgets(LspWidgetsRequest(file_path="Main.lean", line=1, column=1))
    widget_source = client.run_widget_source(
        LspWidgetSourceRequest(file_path="Main.lean", javascript_hash="abc")
    )
    proof = client.run_proof_profile(LspProofProfileRequest(file_path="Main.lean", line=1))

    assert widgets.success is True
    assert widget_source.javascript_hash == "abc"
    assert proof.theorem_name == "t"
    assert [path for path, _ in http.calls] == [
        "/lsp/widgets",
        "/lsp/widget_source",
        "/lsp/proof_profile",
    ]
