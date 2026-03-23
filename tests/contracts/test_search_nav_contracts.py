from lean_mcp_toolkit.contracts.search_nav import (
    LocalDeclFindItem,
    LocalDeclFindRequest,
    LocalDeclFindResponse,
    LocalImportEdgeItem,
    LocalImportFindRequest,
    LocalImportFindResponse,
    LocalRefsFindItem,
    LocalRefsFindRequest,
    LocalRefsFindResponse,
    LocalScopeFindItem,
    LocalScopeFindRequest,
    LocalScopeFindResponse,
    LocalTextFindItem,
    LocalTextFindRequest,
    LocalTextFindResponse,
    RepoNavFileOutlineRequest,
    RepoNavFileOutlineResponse,
    RepoNavReadRequest,
    RepoNavReadResponse,
    RepoNavReadWindow,
    RepoNavResolution,
    RepoNavTreeEntry,
    RepoNavTreePage,
    RepoNavTreeRequest,
    RepoNavTreeResponse,
)


def test_repo_nav_tree_contract_roundtrip() -> None:
    req = RepoNavTreeRequest.from_dict({"base": "Mathlib", "depth": 2, "limit": 50})
    assert req.base == "Mathlib"
    assert req.depth == 2
    assert req.limit == 50

    resp = RepoNavTreeResponse(
        success=True,
        resolution=RepoNavResolution(
            repo_root="/tmp/p",
            source_root="/tmp/p",
            base_path="Mathlib",
            base_module="Mathlib",
        ),
        entries=(
            RepoNavTreeEntry(
                kind="file",
                name="Basic.lean",
                relative_path="Mathlib/Basic.lean",
                module_path="Mathlib.Basic",
            ),
        ),
        page=RepoNavTreePage(offset=0, limit=50, returned=1, next_offset=None),
    )
    loaded = RepoNavTreeResponse.from_dict(resp.to_dict())
    assert loaded.success is True
    assert loaded.entries[0].module_path == "Mathlib.Basic"


def test_repo_nav_outline_and_read_roundtrip() -> None:
    req = RepoNavFileOutlineRequest.from_dict({"target": "A.B"})
    assert req.target == "A.B"

    outline = RepoNavFileOutlineResponse.from_dict(
        {
            "success": True,
            "target": {"file_path": "A/B.lean", "module_path": "A.B"},
            "imports": ["Mathlib"],
            "module_doc": "doc",
            "sections": [{"title": "s", "line_start": 1, "line_end": 2}],
            "declarations": [
                {
                    "decl_kind": "def",
                    "full_name": "A.B.foo",
                    "line_start": 3,
                    "header_preview": "def foo := 1",
                }
            ],
            "scope_cmds": [{"kind": "namespace", "target": "A.B", "line_start": 1}],
            "summary": {"total_lines": 10, "decl_count": 1},
        }
    )
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "A.B"

    read_req = RepoNavReadRequest.from_dict({"target": "A/B.lean", "start_line": 1})
    assert read_req.start_line == 1
    read_resp = RepoNavReadResponse(
        success=True,
        target=outline.target,
        window=RepoNavReadWindow(
            start_line=1,
            end_line=2,
            total_lines=10,
            truncated=True,
            next_start_line=3,
        ),
        content="1 | a\n2 | b",
    )
    loaded = RepoNavReadResponse.from_dict(read_resp.to_dict())
    assert loaded.window is not None
    assert loaded.window.next_start_line == 3


def test_local_search_contracts_roundtrip() -> None:
    decl_req = LocalDeclFindRequest.from_dict({"query": "map", "decl_kinds": ["def"]})
    assert decl_req.decl_kinds == ("def",)
    decl_resp = LocalDeclFindResponse(
        success=True,
        query="map",
        count=1,
        items=(
            LocalDeclFindItem(
                full_name="List.map",
                short_name="map",
                decl_kind="def",
                module_path="Mathlib.Data.List.Basic",
                file_path="Mathlib/Data/List/Basic.lean",
                line_start=10,
            ),
        ),
    )
    assert LocalDeclFindResponse.from_dict(decl_resp.to_dict()).items[0].short_name == "map"

    import_req = LocalImportFindRequest.from_dict({"query": "Mathlib", "direction": "imports"})
    assert import_req.direction == "imports"
    import_resp = LocalImportFindResponse(
        success=True,
        query="Mathlib",
        count=1,
        edges=(
            LocalImportEdgeItem(
                importer_module="A.B",
                importer_file="A/B.lean",
                imported_module="Mathlib",
                line_start=1,
                line_end=1,
            ),
        ),
    )
    assert LocalImportFindResponse.from_dict(import_resp.to_dict()).count == 1

    scope_req = LocalScopeFindRequest.from_dict({"scope_kinds": ["namespace"]})
    assert scope_req.scope_kinds == ("namespace",)
    scope_resp = LocalScopeFindResponse(
        success=True,
        count=1,
        items=(
            LocalScopeFindItem(
                scope_kind="namespace",
                target="A.B",
                file_path="A/B.lean",
                module_path="A.B",
                line_start=1,
                snippet="1 | namespace A.B",
            ),
        ),
    )
    assert LocalScopeFindResponse.from_dict(scope_resp.to_dict()).items[0].scope_kind == "namespace"

    text_req = LocalTextFindRequest.from_dict({"query": "compact", "text_match": "word"})
    assert text_req.text_match == "word"
    text_resp = LocalTextFindResponse(
        success=True,
        query="compact",
        count=1,
        items=(
            LocalTextFindItem(
                scope="decl_doc",
                file_path="A/B.lean",
                module_path="A.B",
                line_start=2,
                line_end=4,
                snippet="2 | /-- compact -/",
            ),
        ),
    )
    assert LocalTextFindResponse.from_dict(text_resp.to_dict()).items[0].scope == "decl_doc"

    refs_req = LocalRefsFindRequest.from_dict({"symbol": "A.B.foo"})
    assert refs_req.symbol == "A.B.foo"
    refs_resp = LocalRefsFindResponse(
        success=True,
        symbol="A.B.foo",
        count=1,
        items=(
            LocalRefsFindItem(
                file_path="A/B.lean",
                module_path="A.B",
                line_start=10,
                column_start=5,
                scope="body",
                snippet="10 | exact A.B.foo",
                is_definition_site=False,
                matched_as="full_name",
            ),
        ),
    )
    assert LocalRefsFindResponse.from_dict(refs_resp.to_dict()).items[0].matched_as == "full_name"
