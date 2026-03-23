from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavReadRequest,
    MathlibNavTreeRequest,
)
from lean_mcp_toolkit.groups.mathlib_nav.service_impl import MathlibNavServiceImpl


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_project_with_mathlib(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    mathlib = project / ".lake" / "packages" / "mathlib" / "Mathlib"
    _write(
        mathlib / "Linear" / "Probe.lean",
        """\
/-! # Probe -/
import Mathlib.Data.Nat.Basic

namespace Linear

/-- test decl -/
def probe : Nat := 1

end Linear
""",
    )
    return project


def test_mathlib_nav_service_tree_outline_read(tmp_path: Path) -> None:
    project = _build_project_with_mathlib(tmp_path)
    svc = MathlibNavServiceImpl(config=ToolkitConfig())

    tree = svc.run_mathlib_nav_tree(
        MathlibNavTreeRequest.from_dict(
            {
                "project_root": str(project),
                "base": "Linear",
                "depth": 1,
                "limit": 20,
            }
        )
    )
    assert tree.success is True
    assert any(e.relative_path == "Linear/Probe.lean" for e in tree.entries)

    outline = svc.run_mathlib_nav_file_outline(
        MathlibNavFileOutlineRequest.from_dict(
            {
                "project_root": str(project),
                "target": "Linear.Probe",
            }
        )
    )
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "Linear.Probe"
    assert "Mathlib.Data.Nat.Basic" in outline.imports
    assert any(d.full_name == "Linear.probe" for d in outline.declarations)

    read = svc.run_mathlib_nav_read(
        MathlibNavReadRequest.from_dict(
            {
                "project_root": str(project),
                "target": "Linear/Probe.lean",
                "start_line": 1,
                "max_lines": 4,
            }
        )
    )
    assert read.success is True
    assert read.window is not None
    assert read.window.start_line == 1


def test_mathlib_nav_service_explicit_mathlib_root(tmp_path: Path) -> None:
    project = _build_project_with_mathlib(tmp_path)
    explicit_root = project / ".lake" / "packages" / "mathlib"
    svc = MathlibNavServiceImpl(config=ToolkitConfig())

    tree = svc.run_mathlib_nav_tree(
        MathlibNavTreeRequest.from_dict(
            {
                "mathlib_root": str(explicit_root),
                "base": "Linear",
                "depth": 0,
            }
        )
    )
    assert tree.success is True
    assert any(e.name == "Probe.lean" for e in tree.entries)
