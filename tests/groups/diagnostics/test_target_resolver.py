from pathlib import Path

from lean_mcp_toolkit.backends.lean.path import TargetResolver



def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")



def test_resolve_non_recursive_directory(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Top.lean", "theorem top : True := by trivial\n")
    _write(tmp_path / "A" / "Sub" / "Nested.lean", "theorem n : True := by trivial\n")

    resolver = TargetResolver()
    resolved = resolver.resolve(project_root=tmp_path, targets=["A"])

    dots = [m.dot for m in resolved.modules]
    assert dots == ["A.Top"]



def test_resolve_topological_order(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "Basic.lean", "theorem b : True := by trivial\n")
    _write(
        tmp_path / "A" / "Advanced.lean",
        "import A.Basic\n\n theorem a : True := by exact A.Basic.b\n",
    )

    resolver = TargetResolver()
    resolved = resolver.resolve(project_root=tmp_path, targets=["A/Advanced.lean", "A/Basic.lean"])
    dots = [m.dot for m in resolved.modules]
    assert dots == ["A.Basic", "A.Advanced"]
