from pathlib import Path

import pytest

from lean_mcp_toolkit.backends.lean.path import resolve_project_root


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_resolve_project_root_walks_up_from_nested_directory(tmp_path: Path) -> None:
    _write(tmp_path / "lakefile.toml", "name = \"Demo\"\n")
    nested = tmp_path / "Pkg" / "Node"
    nested.mkdir(parents=True, exist_ok=True)

    resolved = resolve_project_root(nested)

    assert resolved == tmp_path.resolve()


def test_resolve_project_root_walks_up_from_file_path(tmp_path: Path) -> None:
    _write(tmp_path / "lean-toolchain", "leanprover/lean4:v4.28.0\n")
    target = tmp_path / "Pkg" / "Main.lean"
    _write(target, "def x := 1\n")

    resolved = resolve_project_root(target)

    assert resolved == tmp_path.resolve()


def test_resolve_project_root_falls_back_to_existing_dir_when_no_markers(tmp_path: Path) -> None:
    nested = tmp_path / "Pkg" / "Node"
    nested.mkdir(parents=True, exist_ok=True)

    resolved = resolve_project_root(nested)

    assert resolved == nested.resolve()


def test_resolve_project_root_requires_explicit_path_when_cwd_fallback_disabled(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project_root is required"):
        resolve_project_root(
            None,
            default_project_root=None,
            allow_cwd_fallback=False,
        )
