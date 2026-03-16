from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.diagnostics import BuildRequest, LintRequest
from lean_mcp_toolkit.groups.diagnostics.service_impl import DiagnosticsServiceImpl


def _has_lean_toolchain() -> bool:
    if shutil.which("lake") is None:
        return False
    if shutil.which("lean") is None:
        return False
    return True


def _init_lake_project(base_dir: Path, project_name: str) -> tuple[Path, Path]:
    subprocess.run(
        ["lake", "init", project_name],
        cwd=base_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    project_root = base_dir
    package_dir = project_root / project_name
    return project_root, package_dir


def _new_service(project_root: Path) -> DiagnosticsServiceImpl:
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(project_root)}})
    return DiagnosticsServiceImpl(config=cfg)


def _contains_text_in_items(resp, needle: str) -> bool:
    for file_diag in resp.files:
        for item in file_diag.items:
            if needle in item.data:
                return True
    return False


@pytest.mark.skipif(not _has_lean_toolchain(), reason="real integration test requires lean/lake")
def test_build_dependency_and_artifact_scenarios(tmp_path: Path) -> None:
    # Scenario A: B depends on A, compare build_deps off/on.
    root_a = tmp_path / "case_ab_dep"
    root_a.mkdir(parents=True, exist_ok=True)
    project_root, package_dir = _init_lake_project(root_a, "DiagMatrix")
    service = _new_service(project_root)

    (package_dir / "A.lean").write_text("def foo : Nat := 1\n", encoding="utf-8")
    (package_dir / "B.lean").write_text("import DiagMatrix.A\n#eval foo\n", encoding="utf-8")

    no_deps = service.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/B.lean"],
                "build_deps": False,
                "emit_artifacts": False,
            }
        )
    )
    assert no_deps.success is False
    assert no_deps.failed_stage == "diagnostics"
    assert _contains_text_in_items(no_deps, "unknown module prefix")

    with_deps = service.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/B.lean"],
                "build_deps": True,
                "emit_artifacts": False,
            }
        )
    )
    assert with_deps.success is True
    assert with_deps.failed_stage is None

    # Scenario B: compile A with emit_artifacts, then B can pass without build_deps.
    root_b = tmp_path / "case_emit_then_use"
    root_b.mkdir(parents=True, exist_ok=True)
    project_root_b, package_dir_b = _init_lake_project(root_b, "DiagMatrix")
    service_b = _new_service(project_root_b)

    (package_dir_b / "A.lean").write_text("def foo : Nat := 1\n", encoding="utf-8")
    (package_dir_b / "B.lean").write_text("import DiagMatrix.A\n#eval foo\n", encoding="utf-8")

    build_a_emit = service_b.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/A.lean"],
                "build_deps": False,
                "emit_artifacts": True,
            }
        )
    )
    assert build_a_emit.success is True
    assert build_a_emit.failed_stage is None

    b_without_deps_after_emit = service_b.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/B.lean"],
                "build_deps": False,
                "emit_artifacts": False,
            }
        )
    )
    assert b_without_deps_after_emit.success is True
    assert b_without_deps_after_emit.failed_stage is None

    # Scenario C: A is modified after artifact exists; compare build_deps off/on.
    (package_dir_b / "A.lean").write_text("def foo : Nat :=\n", encoding="utf-8")

    b_without_deps_after_a_change = service_b.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/B.lean"],
                "build_deps": False,
                "emit_artifacts": False,
            }
        )
    )
    assert b_without_deps_after_a_change.success is True
    assert b_without_deps_after_a_change.failed_stage is None

    b_with_deps_after_a_change = service_b.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/B.lean"],
                "build_deps": True,
                "emit_artifacts": False,
            }
        )
    )
    assert b_with_deps_after_a_change.success is False
    assert b_with_deps_after_a_change.failed_stage == "build_deps"
    assert b_with_deps_after_a_change.stage_error_message is not None

    # Scenario D: direct build_deps failure on A returns stage failure and empty files.
    a_with_deps_after_a_change = service_b.run_build(
        BuildRequest.from_dict(
            {
                "targets": ["DiagMatrix/A.lean"],
                "build_deps": True,
                "emit_artifacts": False,
            }
        )
    )
    assert a_with_deps_after_a_change.success is False
    assert a_with_deps_after_a_change.failed_stage == "build_deps"
    assert len(a_with_deps_after_a_change.files) == 0


@pytest.mark.skipif(not _has_lean_toolchain(), reason="real integration test requires lean/lake")
def test_lint_no_sorry_detects_sorry_variants(tmp_path: Path) -> None:
    root = tmp_path / "case_sorry"
    root.mkdir(parents=True, exist_ok=True)
    project_root, package_dir = _init_lake_project(root, "DiagMatrix")
    service = _new_service(project_root)

    (package_dir / "S1.lean").write_text("theorem t1 : True := by\n  sorry\n", encoding="utf-8")
    (package_dir / "S2.lean").write_text("theorem t2 : True := by\n  admit\n", encoding="utf-8")
    (package_dir / "S3.lean").write_text(
        "theorem t3 : True := by\n  exact True.intro\n",
        encoding="utf-8",
    )

    result = service.run_lint_no_sorry(
        LintRequest.from_dict(
            {
                "targets": [
                    "DiagMatrix/S1.lean",
                    "DiagMatrix/S2.lean",
                    "DiagMatrix/S3.lean",
                ],
                "include_content": True,
                "context_lines": 1,
                "timeout_seconds": 120,
            }
        )
    )

    assert result.success is False
    assert len(result.sorries) == 2
    files = {item.fileName for item in result.sorries}
    assert files == {"DiagMatrix.S1", "DiagMatrix.S2"}
    assert all((item.kind or "") == "hasSorry" for item in result.sorries)
    assert all("sorry" in item.data.lower() for item in result.sorries)
