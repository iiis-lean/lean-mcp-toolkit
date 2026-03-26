from lean_mcp_toolkit.contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspProofProfileResponse,
    LspWidgetSourceRequest,
    LspWidgetSourceResponse,
    LspWidgetsRequest,
    LspWidgetsResponse,
)


def test_lsp_widgets_contract_roundtrip() -> None:
    req = LspWidgetsRequest.from_dict(
        {"project_root": "/tmp/demo", "file_path": "Main.lean", "line": 3, "column": 5}
    )
    assert req.to_dict()["column"] == 5

    resp = LspWidgetsResponse.from_dict(
        {
            "success": True,
            "widgets": [
                {
                    "widget_id": "widget-1",
                    "javascript_hash": "abc",
                    "name": "Foo",
                    "range": {
                        "start": {"line": 1, "column": 2},
                        "end": {"line": 1, "column": 8},
                    },
                    "props": {"html": "<b>x</b>"},
                    "raw": {"id": "widget-1"},
                }
            ],
            "count": 1,
        }
    )
    assert resp.success is True
    assert resp.widgets[0].range is not None
    assert resp.widgets[0].raw["id"] == "widget-1"


def test_lsp_widget_source_contract_roundtrip() -> None:
    req = LspWidgetSourceRequest.from_dict(
        {"file_path": "Main.lean", "javascript_hash": "abc"}
    )
    assert req.to_dict()["javascript_hash"] == "abc"

    resp = LspWidgetSourceResponse.from_dict(
        {
            "success": True,
            "javascript_hash": "abc",
            "source_text": "console.log(1)",
            "raw_source": {"sourcetext": "console.log(1)"},
        }
    )
    assert resp.success is True
    assert resp.raw_source == {"sourcetext": "console.log(1)"}


def test_lsp_proof_profile_contract_roundtrip() -> None:
    req = LspProofProfileRequest.from_dict(
        {"file_path": "Main.lean", "line": 10, "top_n": 3, "timeout_seconds": 12}
    )
    assert req.to_dict()["top_n"] == 3

    resp = LspProofProfileResponse.from_dict(
        {
            "success": True,
            "theorem_name": "Foo.bar",
            "total_ms": 33.2,
            "lines": [{"line": 11, "ms": 20.1, "text": "simp"}],
            "count": 1,
            "categories": [{"name": "elaboration", "ms": 30.0}],
            "category_count": 1,
        }
    )
    assert resp.success is True
    assert resp.lines[0].ms == 20.1
    assert resp.categories[0].name == "elaboration"

