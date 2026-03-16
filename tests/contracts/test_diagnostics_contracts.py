from lean_mcp_toolkit.contracts.diagnostics import (
    BuildRequest,
    BuildResponse,
    DiagnosticItem,
    FileDiagnostics,
    LintResponse,
    NoSorryResult,
    Position,
)


def test_build_request_roundtrip() -> None:
    req = BuildRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "targets": ["A.B", "C/D.lean"],
            "build_deps": True,
            "emit_artifacts": False,
            "include_content": True,
            "context_lines": 3,
            "timeout_seconds": 120,
        }
    )
    data = req.to_dict()
    assert data["project_root"] == "/tmp/proj"
    assert data["targets"] == ["A.B", "C/D.lean"]
    assert data["build_deps"] is True
    assert data["context_lines"] == 3


def test_build_response_markdown() -> None:
    item = DiagnosticItem(
        severity="error",
        pos=Position(line=1, column=2),
        endPos=None,
        kind="typeMismatch",
        data="type mismatch",
        fileName="A.B",
        content="theorem t : True := by\n  exact False.elim ?h",
    )
    file_diag = FileDiagnostics(file="A.B", success=False, items=(item,))
    resp = BuildResponse(
        success=False,
        files=(file_diag,),
        failed_stage="diagnostics",
        stage_error_message=None,
    )

    md = resp.to_markdown()
    assert "Build Diagnostics" in md
    assert "A.B" in md
    assert "type mismatch" in md
    assert "failed_stage" in md


def test_lint_response_parsing_no_sorry() -> None:
    raw = {
        "success": False,
        "checks": [
            {
                "check_id": "no_sorry",
                "success": False,
                "message": "found sorry",
                "sorries": [
                    {
                        "severity": "warning",
                        "pos": {"line": 10, "column": 3},
                        "endPos": None,
                        "kind": "hasSorry",
                        "data": "declaration uses sorry",
                        "fileName": "A.C",
                        "content": "by\n  sorry",
                    }
                ],
            }
        ],
    }
    resp = LintResponse.from_dict(raw)
    assert resp.success is False
    assert len(resp.checks) == 1
    first = resp.checks[0]
    assert isinstance(first, NoSorryResult)
    assert first.check_id == "no_sorry"
    assert len(first.sorries) == 1


def test_build_response_stage_fields_roundtrip() -> None:
    raw = {
        "success": False,
        "files": [],
        "failed_stage": "build_deps",
        "stage_error_message": "build_deps failed with returncode=1",
    }
    resp = BuildResponse.from_dict(raw)
    assert resp.failed_stage == "build_deps"
    assert resp.stage_error_message is not None
    dumped = resp.to_dict()
    assert dumped["failed_stage"] == "build_deps"
