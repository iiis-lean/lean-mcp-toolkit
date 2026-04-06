from lean_mcp_toolkit.contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavFileOutlineResponse,
    MathlibNavGrepRequest,
    MathlibNavGrepResponse,
    MathlibNavReadRequest,
    MathlibNavReadResponse,
    MathlibNavTreeRequest,
    MathlibNavTreeResponse,
)


def test_mathlib_nav_tree_contract_roundtrip() -> None:
    req = MathlibNavTreeRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "base": "Mathlib.Data",
            "depth": 2,
            "limit": 20,
        }
    )
    assert req.project_root == "/tmp/proj"
    assert req.base == "Mathlib.Data"
    assert req.depth == 2
    assert req.limit == 20

    resp = MathlibNavTreeResponse.from_dict(
        {
            "success": True,
            "resolution": {
                "repo_root": "/tmp/proj/.lake/packages/mathlib/Mathlib",
                "source_root": "/tmp/proj/.lake/packages/mathlib/Mathlib",
                "base_path": ".",
                "base_module": None,
            },
            "entries": [{"kind": "file", "name": "Basic.lean", "relative_path": "Basic.lean"}],
            "page": {"offset": 0, "limit": 20, "returned": 1, "next_offset": None},
        }
    )
    assert resp.success is True
    assert resp.entries[0].name == "Basic.lean"


def test_mathlib_nav_outline_and_read_contract_roundtrip() -> None:
    req = MathlibNavFileOutlineRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "target": "Mathlib.Init",
            "include_imports": True,
        }
    )
    assert req.target == "Mathlib.Init"
    assert req.include_imports is True

    outline = MathlibNavFileOutlineResponse.from_dict(
        {
            "success": True,
            "target": {"file_path": "Init.lean", "module_path": "Init"},
            "imports": ["Mathlib"],
            "sections": [],
            "declarations": [],
            "scope_cmds": [],
            "summary": {"total_lines": 10, "decl_count": 0},
        }
    )
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "Init"

    read_req = MathlibNavReadRequest.from_dict({"target": "Init.lean", "start_line": 1})
    assert read_req.start_line == 1

    read_resp = MathlibNavReadResponse.from_dict(
        {
            "success": True,
            "target": {"file_path": "Init.lean", "module_path": "Init"},
            "window": {
                "start_line": 1,
                "end_line": 1,
                "total_lines": 1,
                "truncated": False,
            },
            "content": "1 | def x := 1",
        }
    )
    assert read_resp.success is True
    assert read_resp.window is not None
    assert read_resp.window.total_lines == 1

    grep_req = MathlibNavGrepRequest.from_dict(
        {
            "project_root": "/tmp/proj",
            "query": "prime degree",
            "base": "Mathlib.GroupTheory",
            "match_mode": "phrase",
        }
    )
    assert grep_req.base == "Mathlib.GroupTheory"

    grep_resp = MathlibNavGrepResponse.from_dict(
        {
            "success": True,
            "query": "prime degree",
            "match_mode": "phrase",
            "count": 1,
            "items": [
                {
                    "scope": "decl_header",
                    "file_path": "GroupTheory/Burnside.lean",
                    "module_path": "GroupTheory.Burnside",
                    "line_start": 12,
                    "line_end": 12,
                    "snippet": "12 | theorem burnside_prime_degree ...",
                }
            ],
        }
    )
    assert grep_resp.success is True
    assert grep_resp.items[0].module_path == "GroupTheory.Burnside"
