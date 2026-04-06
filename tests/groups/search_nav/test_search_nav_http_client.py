from dataclasses import dataclass

from lean_mcp_toolkit.contracts.search_nav import (
    LocalDeclFindRequest,
    LocalImportFindRequest,
    LocalRefsFindRequest,
    LocalScopeFindRequest,
    LocalTextFindRequest,
    RepoNavGrepRequest,
    RepoNavFileOutlineRequest,
    RepoNavReadRequest,
    RepoNavTreeRequest,
)
from lean_mcp_toolkit.groups.search_nav.client_http import SearchNavHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        _ = payload
        if path == "/search/repo_nav/tree":
            return {"success": True, "entries": [{"kind": "file", "name": "A.lean"}]}
        if path == "/search/repo_nav/file_outline":
            return {
                "success": True,
                "target": {"file_path": "A.lean", "module_path": "A"},
                "imports": [],
                "declarations": [],
                "scope_cmds": [],
                "summary": {"total_lines": 1, "decl_count": 0},
            }
        if path == "/search/repo_nav/grep":
            return {
                "success": True,
                "query": "x",
                "match_mode": "word",
                "path_filter": "A",
                "count": 1,
                "items": [{"scope": "body"}],
            }
        if path == "/search/repo_nav/read":
            return {
                "success": True,
                "target": {"file_path": "A.lean", "module_path": "A"},
                "window": {"start_line": 1, "end_line": 1, "total_lines": 1, "truncated": False},
                "content": "1 | def x := 1",
            }
        if path == "/search/local_decl/find":
            return {"success": True, "query": "x", "count": 1, "items": [{"full_name": "A.x"}]}
        if path == "/search/local_import/find":
            return {"success": True, "query": "A", "count": 1, "edges": [{"imported_module": "A"}]}
        if path == "/search/local_scope/find":
            return {"success": True, "count": 1, "items": [{"scope_kind": "namespace"}]}
        if path == "/search/local_text/find":
            return {"success": True, "query": "doc", "count": 1, "items": [{"scope": "decl_doc"}]}
        if path == "/search/local_refs/find":
            return {"success": True, "symbol": "A.x", "count": 1, "items": [{"scope": "body"}]}
        raise AssertionError(f"unexpected path: {path}")


def test_search_nav_http_client_roundtrip() -> None:
    client = SearchNavHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=_FakeHttpJsonClient(),
    )

    tree = client.run_repo_nav_tree(RepoNavTreeRequest.from_dict({}))
    assert tree.success is True
    assert tree.entries[0].name == "A.lean"

    outline = client.run_repo_nav_file_outline(RepoNavFileOutlineRequest.from_dict({"target": "A"}))
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "A"

    grep = client.run_repo_nav_grep(RepoNavGrepRequest.from_dict({"query": "x"}))
    assert grep.success is True
    assert grep.match_mode == "word"
    assert grep.count == 1

    read = client.run_repo_nav_read(RepoNavReadRequest.from_dict({"target": "A.lean"}))
    assert read.success is True
    assert read.window is not None
    assert read.window.total_lines == 1

    decl = client.run_local_decl_find(LocalDeclFindRequest.from_dict({"query": "x"}))
    assert decl.success is True
    assert decl.count == 1

    imp = client.run_local_import_find(LocalImportFindRequest.from_dict({"query": "A"}))
    assert imp.success is True
    assert imp.count == 1

    scope = client.run_local_scope_find(LocalScopeFindRequest.from_dict({}))
    assert scope.success is True
    assert scope.count == 1

    text = client.run_local_text_find(LocalTextFindRequest.from_dict({"query": "doc"}))
    assert text.success is True
    assert text.count == 1

    refs = client.run_local_refs_find(LocalRefsFindRequest.from_dict({"symbol": "A.x"}))
    assert refs.success is True
    assert refs.count == 1
