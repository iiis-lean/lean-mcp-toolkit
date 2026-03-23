from lean_mcp_toolkit.contracts.diagnostics import (
    AxiomAuditResult,
    BuildRequest,
    BuildResponse,
    DiagnosticItem,
    FileRequest,
    FileResponse,
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


def test_file_request_response_roundtrip() -> None:
    req = FileRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "file_path": "A/B.lean",
            "include_content": True,
            "context_lines": 1,
            "timeout_seconds": 10,
        }
    )
    dumped = req.to_dict()
    assert dumped["file_path"] == "A/B.lean"
    assert dumped["include_content"] is True

    item = DiagnosticItem(
        severity="warning",
        pos=Position(line=2, column=3),
        endPos=None,
        kind="hasSorry",
        data="declaration uses sorry",
        fileName="A.B",
        content="by\n  sorry",
    )
    resp = FileResponse(
        success=True,
        error_message=None,
        file="A.B",
        items=(item,),
        total_items=1,
        error_count=0,
        warning_count=1,
        info_count=0,
        sorry_count=1,
    )
    loaded = FileResponse.from_dict(resp.to_dict())
    assert loaded.file == "A.B"
    assert loaded.warning_count == 1
    assert loaded.items[0].kind == "hasSorry"


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


def test_axiom_audit_markdown_sections() -> None:
    result = AxiomAuditResult.from_dict(
        {
            "check_id": "axiom_audit",
            "success": False,
            "message": "found issues",
            "declared_axioms": [
                {
                    "fileName": "A.C",
                    "declaration": "A.C.ax1",
                    "kind": "axiom",
                    "pos": {"line": 2, "column": 1},
                    "endPos": None,
                    "content": "axiom ax1 : False",
                }
            ],
            "usage_issues": [
                {
                    "fileName": "A.D",
                    "declaration": "A.D.t",
                    "risky_axioms": ["MyAxiom"],
                }
            ],
            "unresolved": [
                {
                    "fileName": "A.E",
                    "declaration": "A.E.u",
                    "reason": "missing probe output",
                }
            ],
        }
    )
    md = result.to_markdown()
    assert "##### Declared Axioms" in md
    assert "##### Axiom Usage Issues" in md
    assert "##### Unresolved Declarations" in md
    assert "error: A/C.lean:2:1: declared axiom `A.C.ax1` (kind=axiom)" in md
    assert "error: A/D.lean: declaration `A.D.t` uses risky axioms: MyAxiom" in md
    assert "error: A/E.lean: declaration `A.E.u` unresolved: missing probe output" in md


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
