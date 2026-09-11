from pathlib import Path

import pytest

from lean_mcp_toolkit.groups.declarations.paths import normalize_single_target


def _write(path: Path, text: str = "theorem sample : True := by trivial\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("input_kind", ["relative", "absolute", "dot"])
def test_normalize_single_target_preserves_regular_file_and_module_identity(
    tmp_path: Path,
    input_kind: str,
) -> None:
    target_file = tmp_path / "A" / "B.lean"
    _write(target_file)
    target = {
        "relative": "A/B.lean",
        "absolute": str(target_file.resolve()),
        "dot": "A.B",
    }[input_kind]

    normalized = normalize_single_target(project_root=tmp_path, target=target)

    assert normalized.relative_file == "A/B.lean"
    assert normalized.module_dot == "A.B"


@pytest.mark.parametrize("input_kind", ["relative", "absolute"])
def test_normalize_single_target_preserves_hidden_file_without_fake_module(
    tmp_path: Path,
    input_kind: str,
) -> None:
    target_file = tmp_path / ".lean_constellation" / "source" / "lean" / "Hidden.lean"
    _write(target_file)
    target = (
        ".lean_constellation/source/lean/Hidden.lean"
        if input_kind == "relative"
        else str(target_file.resolve())
    )

    normalized = normalize_single_target(project_root=tmp_path, target=target)

    assert normalized.relative_file == ".lean_constellation/source/lean/Hidden.lean"
    assert normalized.module_dot is None


def test_normalize_single_target_rejects_relative_path_escape(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write(tmp_path / "Outside.lean")

    with pytest.raises(ValueError, match="relative target outside project_root"):
        normalize_single_target(project_root=project_root, target="../Outside.lean")


def test_normalize_single_target_rejects_absolute_path_escape(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "Outside.lean"
    _write(outside)

    with pytest.raises(ValueError, match="absolute target outside project_root"):
        normalize_single_target(project_root=project_root, target=str(outside.resolve()))


def test_normalize_single_target_rejects_symlink_escape(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "Outside.lean"
    _write(outside)
    (project_root / "Linked.lean").symlink_to(outside)

    with pytest.raises(ValueError, match="relative target outside project_root"):
        normalize_single_target(project_root=project_root, target="Linked.lean")


def test_normalize_single_target_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "Source").mkdir()

    with pytest.raises(ValueError, match="directory target is not supported"):
        normalize_single_target(project_root=tmp_path, target="Source")


def test_normalize_single_target_rejects_non_lean_file(tmp_path: Path) -> None:
    _write(tmp_path / "notes.txt", "not Lean\n")

    with pytest.raises(ValueError, match="target must be a .lean file"):
        normalize_single_target(project_root=tmp_path, target="notes.txt")
