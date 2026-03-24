from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lean_mcp_toolkit.app.warmup import ToolkitWarmupRunner
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
)
from lean_mcp_toolkit.contracts.diagnostics import FileRequest, FileResponse
from lean_mcp_toolkit.contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclFindResponse,
)


@dataclass(slots=True)
class _FakeSearch:
    calls: list[MathlibDeclFindRequest] = field(default_factory=list)

    def run_mathlib_decl_find(self, req: MathlibDeclFindRequest) -> MathlibDeclFindResponse:
        self.calls.append(req)
        return MathlibDeclFindResponse(
            query=req.query,
            count=1,
            processing_time_ms=1,
            results=tuple(),
        )


@dataclass(slots=True)
class _FakeDeclarations:
    project_root: Path
    targets: list[str] = field(default_factory=list)

    def extract(self, req: DeclarationExtractRequest) -> DeclarationExtractResponse:
        self.targets.append(req.target)
        assert req.target
        assert (self.project_root / req.target).exists()
        return DeclarationExtractResponse(success=True, error_message=None, total_declarations=0)


@dataclass(slots=True)
class _FakeDiagnostics:
    project_root: Path
    files: list[str] = field(default_factory=list)

    def run_file(self, req: FileRequest) -> FileResponse:
        self.files.append(req.file_path)
        assert req.file_path
        assert (self.project_root / req.file_path).exists()
        return FileResponse(
            success=True,
            error_message=None,
            file=req.file_path,
            items=tuple(),
            total_items=0,
            error_count=0,
            warning_count=0,
            info_count=0,
            sorry_count=0,
        )


def test_warmup_runner_success_and_cleanup(tmp_path: Path) -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "warmup": {
                "policy": {
                    "enabled": True,
                    "run_on_startup": True,
                    "continue_on_error": True,
                    "default_project_root": str(tmp_path),
                },
                "plan": {
                    "order": [
                        "search.mathlib_decl.find",
                        "declarations.extract",
                        "diagnostics.file",
                    ]
                },
                "calls": {
                    "search.mathlib_decl.find": {
                        "enabled": True,
                        "request": {"query": "Nat.succ", "limit": 1, "rerank_top": 0},
                    },
                    "declarations.extract": {
                        "enabled": True,
                        "use_probe_file": True,
                        "request": {},
                    },
                    "diagnostics.file": {
                        "enabled": True,
                        "use_probe_file": True,
                        "request": {"include_content": False, "context_lines": 0},
                    },
                },
            }
        }
    )
    fake_search = _FakeSearch()
    fake_decl = _FakeDeclarations(project_root=tmp_path)
    fake_diag = _FakeDiagnostics(project_root=tmp_path)
    runner = ToolkitWarmupRunner(
        config=cfg,
        diagnostics=fake_diag,
        declarations=fake_decl,
        search_core=fake_search,
    )

    report = runner.run()
    assert report.enabled is True
    assert report.executed is True
    assert report.success is True
    assert len(report.steps) == 3
    assert len(fake_search.calls) == 1
    assert len(fake_decl.targets) == 1
    assert len(fake_diag.files) == 1
    probe_rel = fake_decl.targets[0]
    assert probe_rel == fake_diag.files[0]
    assert not (tmp_path / probe_rel).exists()


def test_warmup_runner_probe_conflict_uses_suffix(tmp_path: Path) -> None:
    existing_rel = "LeanMcpToolkitWarmup/Probe.lean"
    existing_abs = tmp_path / existing_rel
    existing_abs.parent.mkdir(parents=True, exist_ok=True)
    existing_abs.write_text("-- existing\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "warmup": {
                "policy": {"enabled": True, "default_project_root": str(tmp_path)},
                "plan": {"order": ["declarations.extract"]},
                "calls": {
                    "declarations.extract": {"enabled": True, "use_probe_file": True, "request": {}}
                },
            }
        }
    )
    fake_decl = _FakeDeclarations(project_root=tmp_path)
    runner = ToolkitWarmupRunner(
        config=cfg,
        diagnostics=None,
        declarations=fake_decl,
        search_core=None,
    )
    report = runner.run()
    assert report.success is True
    assert len(fake_decl.targets) == 1
    generated_rel = fake_decl.targets[0]
    assert generated_rel != existing_rel
    assert existing_abs.read_text(encoding="utf-8") == "-- existing\n"
    assert not (tmp_path / generated_rel).exists()


def test_warmup_runner_probe_without_project_root_fails() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "warmup": {
                "policy": {"enabled": True, "run_on_startup": True},
                "plan": {"order": ["declarations.extract"]},
                "calls": {
                    "declarations.extract": {"enabled": True, "use_probe_file": True, "request": {}}
                },
            }
        }
    )
    runner = ToolkitWarmupRunner(
        config=cfg,
        diagnostics=None,
        declarations=None,
        search_core=None,
    )
    report = runner.run()
    assert report.success is False
    assert len(report.steps) == 1
    assert "project_root" in (report.steps[0].error_message or "")
