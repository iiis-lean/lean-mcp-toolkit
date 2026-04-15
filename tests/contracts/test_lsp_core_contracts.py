from lean_mcp_toolkit.contracts.lsp_core import (
    CodeAction,
    CodeActionEdit,
    LspCodeActionsRequest,
    LspCodeActionsResponse,
    LspFileOutlineRequest,
    LspFileOutlineResponse,
    LspGoalRequest,
    LspGoalResponse,
    LspHoverRequest,
    LspHoverResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    LspTermGoalRequest,
    LspTermGoalResponse,
    OutlineEntry,
)


def test_lsp_requests_roundtrip() -> None:
    req = LspGoalRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "file_path": "A/B.lean",
            "line": 3,
            "column": 12,
        }
    )
    dumped = req.to_dict()
    assert dumped["project_root"] == "/tmp/proj"
    assert dumped["file_path"] == "A/B.lean"
    assert dumped["line"] == 3
    assert dumped["column"] == 12



def test_lsp_file_outline_response_roundtrip() -> None:
    entry = OutlineEntry(
        name="foo",
        kind="theorem",
        start_line=10,
        end_line=12,
        type_signature="True",
    )
    resp = LspFileOutlineResponse(
        success=True,
        imports=("Mathlib",),
        declarations=(entry,),
        total_declarations=1,
    )
    loaded = LspFileOutlineResponse.from_dict(resp.to_dict())
    assert loaded.success is True
    assert loaded.imports == ("Mathlib",)
    assert len(loaded.declarations) == 1
    assert loaded.declarations[0].name == "foo"



def test_lsp_hover_response_roundtrip() -> None:
    resp = LspHoverResponse.from_dict(
        {
            "success": True,
            "symbol": "Nat.succ",
            "info": "Nat -> Nat",
            "diagnostics": [
                {
                    "severity": "warning",
                    "message": "unused",
                    "line": 1,
                    "column": 2,
                }
            ],
        }
    )
    assert resp.success is True
    assert resp.symbol == "Nat.succ"
    assert len(resp.diagnostics) == 1
    assert resp.to_dict()["diagnostics"][0]["severity"] == "warning"



def test_lsp_code_actions_response_roundtrip() -> None:
    action = CodeAction(
        title="Try this",
        is_preferred=True,
        edits=(
            CodeActionEdit(
                new_text="exact h",
                start_line=3,
                start_column=5,
                end_line=3,
                end_column=10,
            ),
        ),
    )
    resp = LspCodeActionsResponse(success=True, actions=(action,))
    loaded = LspCodeActionsResponse.from_dict(resp.to_dict())
    assert loaded.success is True
    assert len(loaded.actions) == 1
    assert loaded.actions[0].title == "Try this"
    assert loaded.actions[0].edits[0].new_text == "exact h"

def test_other_lsp_request_models_roundtrip() -> None:
    assert LspFileOutlineRequest.from_dict({"file_path": "A.lean"}).file_path == "A.lean"
    assert LspTermGoalRequest.from_dict({"file_path": "A.lean", "line": 1}).line == 1
    assert LspHoverRequest.from_dict({"file_path": "A.lean", "line": 1, "column": 1}).column == 1
    assert LspCodeActionsRequest.from_dict({"file_path": "A.lean", "line": 2}).line == 2
    assert LspRunSnippetRequest.from_dict({"code": "#check Nat"}).code == "#check Nat"

    assert LspGoalResponse.from_dict({"success": True}).success is True
    assert LspTermGoalResponse.from_dict({"success": False}).success is False
    assert LspRunSnippetResponse.from_dict({"success": True}).success is True
