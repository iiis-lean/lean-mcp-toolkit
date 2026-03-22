from dataclasses import dataclass

from lean_mcp_toolkit.contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationLocateRequest,
)
from lean_mcp_toolkit.groups.declarations.client_http import DeclarationsHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        if path == "/declarations/extract":
            assert payload["target"] == "A.B"
            return {
                "success": True,
                "error_message": None,
                "total_declarations": 1,
                "declarations": [
                    {
                        "name": "A.B.foo",
                        "kind": "theorem",
                        "signature": "True",
                        "value": ":= by trivial",
                        "full_declaration": "theorem foo : True := by trivial",
                        "docstring": "/-- foo -/",
                        "decl_start_pos": {"line": 1, "column": 0},
                        "decl_end_pos": {"line": 1, "column": 29},
                        "doc_start_pos": {"line": 1, "column": 0},
                        "doc_end_pos": {"line": 1, "column": 10},
                    }
                ],
            }
        if path == "/declarations/locate":
            assert payload["source_file"] == "A/B.lean"
            assert payload["symbol"] == "foo"
            assert payload["line"] == 3
            assert payload["column"] == 9
            return {
                "success": True,
                "error_message": None,
                "source_pos": {"line": 3, "column": 9},
                "target_file_path": "/tmp/A/B.lean",
                "target_range": {
                    "start": {"line": 7, "column": 4},
                    "end": {"line": 7, "column": 7},
                },
                "matched_declaration": {
                    "name": "A.B.foo",
                    "kind": "theorem",
                    "signature": "True",
                    "value": None,
                    "full_declaration": "theorem foo : True := by trivial",
                    "docstring": None,
                    "decl_start_pos": {"line": 7, "column": 0},
                    "decl_end_pos": {"line": 8, "column": 5},
                    "doc_start_pos": None,
                    "doc_end_pos": None,
                },
            }
        raise AssertionError(f"unexpected path: {path}")


def test_declarations_http_client_roundtrip() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = DeclarationsHttpClient(http_config=cfg, http_client=_FakeHttpJsonClient())

    resp = client.extract(DeclarationExtractRequest.from_dict({"target": "A.B"}))

    assert resp.success is True
    assert resp.total_declarations == 1
    assert resp.declarations[0].name == "A.B.foo"


def test_declarations_http_client_locate_roundtrip() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = DeclarationsHttpClient(http_config=cfg, http_client=_FakeHttpJsonClient())

    resp = client.locate(
        DeclarationLocateRequest.from_dict(
            {
                "source_file": "A/B.lean",
                "symbol": "foo",
                "line": 3,
                "column": 9,
            }
        )
    )

    assert resp.success is True
    assert resp.source_pos is not None
    assert resp.source_pos.line == 3
    assert resp.target_file_path == "/tmp/A/B.lean"
    assert resp.matched_declaration is not None
    assert resp.matched_declaration.name == "A.B.foo"
