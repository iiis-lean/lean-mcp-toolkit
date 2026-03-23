from lean_mcp_toolkit.contracts.lsp_assist import (
    CompletionItem,
    DiagnosticMessage,
    LspCompletionsRequest,
    LspCompletionsResponse,
    LspDeclarationFileRequest,
    LspDeclarationFileResponse,
    LspMultiAttemptRequest,
    LspMultiAttemptResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    LspTheoremSoundnessRequest,
    LspTheoremSoundnessResponse,
    Position,
    Range,
    SourceWarning,
)


def test_lsp_assist_requests_roundtrip() -> None:
    comp = LspCompletionsRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "file_path": "A/B.lean",
            "line": 10,
            "column": 5,
            "max_completions": 8,
        }
    )
    assert comp.to_dict()["max_completions"] == 8

    decl = LspDeclarationFileRequest.from_dict(
        {
            "file_path": "A/B.lean",
            "symbol": "foo",
            "line": 3,
            "column": 2,
            "include_file_content": True,
        }
    )
    dumped_decl = decl.to_dict()
    assert dumped_decl["symbol"] == "foo"
    assert dumped_decl["include_file_content"] is True

    multi = LspMultiAttemptRequest.from_dict(
        {
            "file_path": "A/B.lean",
            "line": 5,
            "snippets": ["exact h", "simp"],
            "max_attempts": 1,
        }
    )
    assert multi.snippets == ("exact h", "simp")
    assert multi.max_attempts == 1

    snippet = LspRunSnippetRequest.from_dict({"code": "import Mathlib"})
    assert snippet.code == "import Mathlib"

    soundness = LspTheoremSoundnessRequest.from_dict(
        {"file_path": "A/B.lean", "theorem_name": "A.B.t", "scan_source": False}
    )
    assert soundness.scan_source is False


def test_lsp_assist_responses_roundtrip() -> None:
    comp_resp = LspCompletionsResponse(
        success=True,
        items=(
            CompletionItem(label="foo", kind="function", detail="Nat"),
            CompletionItem(label="bar", kind=None, detail=None),
        ),
        count=2,
    )
    loaded_comp = LspCompletionsResponse.from_dict(comp_resp.to_dict())
    assert loaded_comp.success is True
    assert loaded_comp.count == 2
    assert loaded_comp.items[0].label == "foo"

    decl_resp = LspDeclarationFileResponse(
        success=True,
        source_pos=Position(line=3, column=4),
        target_file_path="/tmp/A/B.lean",
        target_file_uri="file:///tmp/A/B.lean",
        target_range=Range(
            start=Position(line=1, column=1),
            end=Position(line=4, column=1),
        ),
        target_selection_range=None,
        content="theorem t : True := by\n  trivial\n",
    )
    loaded_decl = LspDeclarationFileResponse.from_dict(decl_resp.to_dict())
    assert loaded_decl.success is True
    assert loaded_decl.target_file_path == "/tmp/A/B.lean"
    assert loaded_decl.source_pos is not None
    assert loaded_decl.source_pos.line == 3

    multi_resp = LspMultiAttemptResponse.from_dict(
        {
            "success": True,
            "items": [
                {
                    "snippet": "exact h",
                    "goals": [],
                    "diagnostics": [],
                    "attempt_success": True,
                    "goal_count": 0,
                }
            ],
            "count": 1,
            "any_success": True,
        }
    )
    assert multi_resp.success is True
    assert multi_resp.any_success is True
    assert multi_resp.items[0].snippet == "exact h"

    run_resp = LspRunSnippetResponse.from_dict(
        {
            "success": False,
            "error_message": None,
            "diagnostics": [
                {
                    "severity": "error",
                    "message": "type mismatch",
                    "line": 2,
                    "column": 3,
                }
            ],
            "error_count": 1,
            "warning_count": 0,
            "info_count": 0,
        }
    )
    assert run_resp.success is False
    assert run_resp.error_count == 1
    assert run_resp.diagnostics[0] == DiagnosticMessage(
        severity="error",
        message="type mismatch",
        line=2,
        column=3,
    )

    soundness_resp = LspTheoremSoundnessResponse(
        success=True,
        axioms=("Classical.choice",),
        warnings=(SourceWarning(line=8, pattern="unsafe"),),
        axiom_count=1,
        warning_count=1,
    )
    loaded_soundness = LspTheoremSoundnessResponse.from_dict(soundness_resp.to_dict())
    assert loaded_soundness.success is True
    assert loaded_soundness.axiom_count == 1
    assert loaded_soundness.warnings[0].pattern == "unsafe"

