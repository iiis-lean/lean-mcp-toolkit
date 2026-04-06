from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
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
from lean_mcp_toolkit.groups.search_nav.service_impl import SearchNavServiceImpl


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _write(
        repo / "Foo" / "Bar.lean",
        """\
/-! # Foo.Bar
Module level docs
-/
import Mathlib.Data.Nat.Basic

namespace Foo

/-- declaration docs for foo -/
def foo : Nat := 1

theorem foo_eq : foo = 1 := by
  rfl

open scoped BigOperators
export Nat (succ)
attribute [simp] Nat.succ

end Foo
""",
    )
    _write(
        repo / "Foo" / "Baz.lean",
        """\
import Foo.Bar

namespace Foo

def useFoo : Nat := Foo.foo

end Foo
""",
    )
    return repo


def test_search_nav_service_repo_nav_tools(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    svc = SearchNavServiceImpl(config=ToolkitConfig())

    tree = svc.run_repo_nav_tree(
        RepoNavTreeRequest.from_dict(
            {
                "repo_root": str(repo),
                "base": "Foo",
                "depth": 1,
                "limit": 20,
            }
        )
    )
    assert tree.success is True
    assert any(e.relative_path == "Foo/Bar.lean" for e in tree.entries)
    assert any(e.relative_path == "Foo/Baz.lean" for e in tree.entries)

    outline = svc.run_repo_nav_file_outline(
        RepoNavFileOutlineRequest.from_dict(
            {
                "repo_root": str(repo),
                "target": "Foo.Bar",
            }
        )
    )
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "Foo.Bar"
    assert "Mathlib.Data.Nat.Basic" in outline.imports
    assert outline.module_doc is not None
    assert any(d.full_name == "Foo.foo" for d in outline.declarations)
    assert any(cmd.kind == "open_scoped" for cmd in outline.scope_cmds)

    read = svc.run_repo_nav_read(
        RepoNavReadRequest.from_dict(
            {
                "repo_root": str(repo),
                "target": "Foo/Bar.lean",
                "start_line": 1,
                "max_lines": 5,
                "with_line_numbers": True,
            }
        )
    )
    assert read.success is True
    assert read.window is not None
    assert read.window.start_line == 1
    assert "1 | /-! # Foo.Bar" in read.content


def test_search_nav_service_local_find_tools(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    svc = SearchNavServiceImpl(config=ToolkitConfig())

    decl = svc.run_local_decl_find(
        LocalDeclFindRequest.from_dict(
            {
                "repo_root": str(repo),
                "query": "Foo.",
                "match_mode": "prefix",
            }
        )
    )
    assert decl.success is True
    assert any(item.full_name == "Foo.foo" for item in decl.items)

    imp = svc.run_local_import_find(
        LocalImportFindRequest.from_dict(
            {
                "repo_root": str(repo),
                "query": "Foo.Bar",
                "direction": "imported_by",
                "match_mode": "exact",
            }
        )
    )
    assert imp.success is True
    assert any(edge.importer_module == "Foo.Baz" for edge in imp.edges)

    scope = svc.run_local_scope_find(
        LocalScopeFindRequest.from_dict(
            {
                "repo_root": str(repo),
                "query": "BigOperators",
                "scope_kinds": ["open_scoped"],
            }
        )
    )
    assert scope.success is True
    assert scope.count == 1
    assert scope.items[0].scope_kind == "open_scoped"

    text = svc.run_local_text_find(
        LocalTextFindRequest.from_dict(
            {
                "repo_root": str(repo),
                "query": "declaration docs",
                "scopes": ["decl_doc"],
                "text_match": "phrase",
            }
        )
    )
    assert text.success is True
    assert text.count == 1
    assert text.items[0].scope == "decl_doc"

    refs = svc.run_local_refs_find(
        LocalRefsFindRequest.from_dict(
            {
                "repo_root": str(repo),
                "symbol": "Foo.foo",
                "include_definition_site": False,
                "scopes": ["decl_header", "body"],
            }
        )
    )
    assert refs.success is True
    assert refs.count >= 1
    assert all(item.is_definition_site is False for item in refs.items)
    assert any(item.file_path == "Foo/Baz.lean" for item in refs.items)

    grep = svc.run_repo_nav_grep(
        RepoNavGrepRequest.from_dict(
            {
                "repo_root": str(repo),
                "query": "Foo.foo",
                "match_mode": "word",
                "path_filter": "Foo",
            }
        )
    )
    assert grep.success is True
    assert grep.match_mode == "word"
    assert grep.path_filter == "Foo"
    assert any(item.file_path == "Foo/Baz.lean" for item in grep.items)
