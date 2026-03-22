from lean_mcp_toolkit.contracts.diagnostics import (
    AxiomAuditResult,
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
    ok_diag = FileDiagnostics(file="A.C", success=True, items=tuple())
    resp = BuildResponse(
        success=False,
        files=(file_diag, ok_diag),
        failed_stage="diagnostics",
        stage_error_message=None,
    )

    md = resp.to_markdown()
    assert "Build Diagnostics" in md
    assert "A.B" in md
    assert "type mismatch" in md
    assert "failed_stage" in md
    assert "error: A/B.lean:1:2: type mismatch" in md
    assert "A.C" not in md


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


def test_lint_response_parsing_axiom_audit() -> None:
    raw = {
        "success": False,
        "checks": [
            {
                "check_id": "axiom_audit",
                "success": False,
                "message": "found 1 risky axiom usage item(s); 1 declaration(s) unresolved",
                "declared_axioms": [],
                "usage_issues": [
                    {
                        "fileName": "A.C",
                        "declaration": "A.C.t",
                        "risky_axioms": ["MyAxiom"],
                    }
                ],
                "unresolved": [
                    {
                        "fileName": "A.C",
                        "declaration": "A.C.u",
                        "reason": "axiom report not found in probe output",
                    }
                ],
            }
        ],
    }
    resp = LintResponse.from_dict(raw)
    assert resp.success is False
    assert len(resp.checks) == 1
    first = resp.checks[0]
    assert isinstance(first, AxiomAuditResult)
    assert first.usage_issues[0].declaration == "A.C.t"
    assert first.usage_issues[0].risky_axioms == ("MyAxiom",)
    assert first.unresolved[0].reason == "axiom report not found in probe output"


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
