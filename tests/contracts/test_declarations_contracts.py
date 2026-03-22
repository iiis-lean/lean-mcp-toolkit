from lean_mcp_toolkit.contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationItem,
    DeclarationLocateRange,
    DeclarationLocateRequest,
    DeclarationLocateResponse,
    DeclarationPosition,
)


def test_declaration_extract_request_roundtrip() -> None:
    req = DeclarationExtractRequest.from_dict(
        {
            "project_root": "/tmp/lean-proj",
            "target": "Math.Topology.Basic",
        }
    )
    data = req.to_dict()
    assert data["project_root"] == "/tmp/lean-proj"
    assert data["target"] == "Math.Topology.Basic"


def test_declaration_extract_response_roundtrip() -> None:
    item = DeclarationItem(
        name="Math.Topology.Basic.foo",
        kind="theorem",
        signature="True",
        value="by trivial",
        full_declaration="theorem foo : True := by trivial",
        docstring="/-- foo doc -/",
        decl_start_pos=DeclarationPosition(line=10, column=3),
        decl_end_pos=DeclarationPosition(line=11, column=15),
        doc_start_pos=DeclarationPosition(line=9, column=0),
        doc_end_pos=DeclarationPosition(line=9, column=15),
    )
    resp = DeclarationExtractResponse(
        success=True,
        error_message=None,
        total_declarations=1,
        declarations=(item,),
    )
    dumped = resp.to_dict()
    loaded = DeclarationExtractResponse.from_dict(dumped)
    assert loaded.success is True
    assert loaded.total_declarations == 1
    assert len(loaded.declarations) == 1
    assert loaded.declarations[0].name == "Math.Topology.Basic.foo"
    assert loaded.declarations[0].decl_start_pos is not None
    assert loaded.declarations[0].decl_start_pos.line == 10


def test_declaration_extract_response_markdown() -> None:
    resp = DeclarationExtractResponse(
        success=False,
        error_message="not implemented",
        total_declarations=0,
        declarations=tuple(),
    )
    md = resp.to_markdown()
    assert "Declarations" in md
    assert "success" in md
    assert "not implemented" in md


def test_declaration_locate_request_roundtrip() -> None:
    req = DeclarationLocateRequest.from_dict(
        {
            "project_root": "/tmp/lean-proj",
            "source_file": "Math/Topology/Basic.lean",
            "symbol": "foo",
            "line": 12,
            "column": 7,
        }
    )
    data = req.to_dict()
    assert data["project_root"] == "/tmp/lean-proj"
    assert data["source_file"] == "Math/Topology/Basic.lean"
    assert data["symbol"] == "foo"
    assert data["line"] == 12
    assert data["column"] == 7


def test_declaration_locate_response_roundtrip() -> None:
    decl = DeclarationItem(
        name="Math.Topology.Basic.foo",
        kind="theorem",
        signature="True",
    )
    resp = DeclarationLocateResponse(
        success=True,
        error_message=None,
        source_pos=DeclarationPosition(line=2, column=7),
        target_file_path="/tmp/lean-proj/Math/Topology/Basic.lean",
        target_range=DeclarationLocateRange(
            start=DeclarationPosition(line=10, column=4),
            end=DeclarationPosition(line=10, column=7),
        ),
        matched_declaration=decl,
    )
    dumped = resp.to_dict()
    loaded = DeclarationLocateResponse.from_dict(dumped)
    assert loaded.success is True
    assert loaded.source_pos is not None
    assert loaded.source_pos.line == 2
    assert loaded.target_range is not None
    assert loaded.target_range.start.column == 4
    assert loaded.matched_declaration is not None
    assert loaded.matched_declaration.name == "Math.Topology.Basic.foo"
