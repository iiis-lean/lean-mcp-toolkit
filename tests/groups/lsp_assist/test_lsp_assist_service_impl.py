from dataclasses import dataclass
from pathlib import Path
import time

import pytest

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_assist import (
    LspCompletionsRequest,
    LspDeclarationSoundnessBatchRequest,
    LspDeclarationSoundnessRequest,
    LspDeclarationSoundnessResponse,
    LspDeclarationFileRequest,
    LspMultiAttemptRequest,
    LspRunSnippetRequest,
)
from lean_mcp_toolkit.groups.lsp_assist.service_impl import LspAssistServiceImpl


@dataclass(slots=True)
class _FakeLspClient:
    file_content: str
    target_uri: str
    diag_error: Exception | None = None
    diag_delay_seconds: float = 0.0
    diag_timeouts: list[float] | None = None
    closed_paths: list[list[str]] | None = None
    verify_diagnostics: list[dict[str, object]] | None = None

    def open_file(self, rel_path: str, force_reopen: bool = False) -> None:
        _ = rel_path
        _ = force_reopen

    def close_files(self, paths, blocking: bool = True):
        _ = blocking
        if self.closed_paths is not None:
            self.closed_paths.append(list(paths))

    def get_file_content(self, rel_path: str) -> str:
        _ = rel_path
        return self.file_content

    def get_completions(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return [
            {"label": "foo", "kind": 3, "detail": "foo detail"},
            {"label": "bar", "kind": 6, "detail": "bar detail"},
            {"label": "foobar", "kind": 3, "detail": "foobar detail"},
        ]

    def get_declarations(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return [
            {
                "targetUri": self.target_uri,
                "targetRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 3, "character": 0},
                },
                "targetSelectionRange": {
                    "start": {"line": 0, "character": 4},
                    "end": {"line": 0, "character": 7},
                },
            }
        ]

    def get_definitions(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return []

    def update_file(self, rel_path: str, changes) -> None:
        _ = rel_path, changes

    def update_file_content(self, rel_path: str, content: str) -> None:
        _ = rel_path, content

    def get_goal(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return {"goals": ["⊢ True"]}

    def get_diagnostics(
        self,
        rel_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        inactivity_timeout: float = 15.0,
    ):
        _ = start_line, end_line
        if self.diag_timeouts is not None:
            self.diag_timeouts.append(inactivity_timeout)
        if self.diag_delay_seconds > 0:
            time.sleep(self.diag_delay_seconds)
        if self.diag_error is not None and (
            rel_path.startswith("_mcp_snippet_")
            or rel_path.startswith("_mcp_decl_soundness_")
        ):
            raise self.diag_error
        if rel_path.startswith("_mcp_snippet_"):
            return [
                {
                    "severity": 2,
                    "message": "unused theorem",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 6},
                    },
                }
            ]
        if rel_path.startswith("_mcp_decl_soundness_"):
            if self.verify_diagnostics is not None:
                return self.verify_diagnostics
            return [
                {
                    "severity": 3,
                    "message": "'A.B.t' depends on axioms: [Classical.choice]",
                    "range": {
                        "start": {"line": 1, "character": 0},
                        "end": {"line": 1, "character": 10},
                    },
                }
            ]
        return [
            {
                "severity": 2,
                "message": "diagnostic on attempt",
                "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 4},
                },
            }
        ]


@dataclass(slots=True)
class _FakeLspClientManager:
    client: _FakeLspClient
    recycled_roots: list[Path] | None = None

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client

    def recycle_client(self, project_root: Path) -> None:
        if self.recycled_roots is not None:
            self.recycled_roots.append(project_root.resolve())


def _run_soundness_with_diagnostics(
    tmp_path: Path,
    diagnostics: list[dict[str, object]],
) -> LspDeclarationSoundnessResponse:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.32.0\n", encoding="utf-8")
    target_file = tmp_path / "A" / "B.lean"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("theorem t : True := by trivial\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_assist": {"enabled": True},
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=target_file.resolve().as_uri(),
        verify_diagnostics=diagnostics,
    )
    service = LspAssistServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=fake_client),
    )
    return service.run_declaration_soundness(
        LspDeclarationSoundnessRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "declaration_name": "A.B.t",
                "scan_source": False,
            }
        )
    )


def test_lsp_assist_service_roundtrip(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    target_file = tmp_path / "A" / "B.lean"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("def foo := 1\ntheorem t : True := by\n  trivial\n", encoding="utf-8")
    content = "import A.B\n\ntheorem main : True := by\n  foo\n"
    source_file = tmp_path / "Main.lean"
    source_file.write_text(content, encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_assist": {
                "enabled": True,
                "default_max_completions": 2,
                "declaration_file_include_content_default": True,
            },
        }
    )
    service = LspAssistServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(
            client=_FakeLspClient(file_content=content, target_uri=target_file.resolve().as_uri())
        ),
    )

    comp = service.run_completions(
        LspCompletionsRequest.from_dict(
            {"file_path": "Main.lean", "line": 4, "column": 5}
        )
    )
    assert comp.success is True
    assert comp.count == 2

    decl = service.run_declaration_file(
        LspDeclarationFileRequest.from_dict(
            {"file_path": "Main.lean", "symbol": "foo", "include_file_content": True}
        )
    )
    assert decl.success is True
    assert decl.target_file_path is not None
    assert decl.content is not None

    multi = service.run_multi_attempt(
        LspMultiAttemptRequest.from_dict(
            {
                "file_path": "Main.lean",
                "line": 4,
                "snippets": ["exact trivial", "simp"],
            }
        )
    )
    assert multi.success is True
    assert multi.count == 2
    assert multi.items[0].goal_count == 1

    snippet = service.run_snippet(
        LspRunSnippetRequest.from_dict({"code": "import Mathlib\ndef x := 1\n"})
    )
    assert snippet.success is True
    assert snippet.warning_count == 1

    soundness = service.run_declaration_soundness(
        LspDeclarationSoundnessRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "declaration_name": "A.B.t",
                "scan_source": False,
            }
        )
    )
    assert soundness.success is True
    assert soundness.axiom_count == 1
    assert soundness.axioms == ("Classical.choice",)

    comp_from_nested_root = service.run_completions(
        LspCompletionsRequest.from_dict(
            {
                "project_root": str(tmp_path / "A"),
                "file_path": "Main.lean",
                "line": 4,
                "column": 5,
            }
        )
    )
    assert comp_from_nested_root.success is True


@pytest.mark.parametrize(
    ("message", "expected_axioms"),
    [
        ("'A.B.t' does not depend on any axioms", tuple()),
        ("'A.B.t' depends on axioms: [sorryAx]", ("sorryAx",)),
        (
            "'A.B.t' depends on axioms: [sorryAx, A.B.customAxiom]",
            ("sorryAx", "A.B.customAxiom"),
        ),
        (
            "'A.B.t' depends on axioms: [\n  sorryAx,\n  A.B.customAxiom\n]",
            ("sorryAx", "A.B.customAxiom"),
        ),
    ],
)
def test_lsp_assist_declaration_soundness_resolves_exact_axiom_report(
    tmp_path: Path,
    message: str,
    expected_axioms: tuple[str, ...],
) -> None:
    response = _run_soundness_with_diagnostics(
        tmp_path,
        [{"severity": 3, "message": message}],
    )

    assert response.success is True
    assert response.error_message is None
    assert response.axioms == expected_axioms
    assert response.axiom_count == len(expected_axioms)


@pytest.mark.parametrize(
    ("diagnostics", "error_fragment"),
    [
        ([{"severity": 3, "message": "unrelated information"}], "not found"),
        (
            [{"severity": 3, "message": "'A.B.other' does not depend on any axioms"}],
            "unexpected",
        ),
        (
            [
                {"severity": 3, "message": "'A.B.t' does not depend on any axioms"},
                {"severity": 3, "message": "'A.B.other' depends on axioms: [sorryAx]"},
            ],
            "unexpected",
        ),
    ],
)
def test_lsp_assist_declaration_soundness_fails_closed_on_unresolved_report(
    tmp_path: Path,
    diagnostics: list[dict[str, object]],
    error_fragment: str,
) -> None:
    response = _run_soundness_with_diagnostics(tmp_path, diagnostics)

    assert response.success is False
    assert error_fragment in (response.error_message or "")
    assert response.axioms == tuple()


def test_lsp_assist_declaration_soundness_batch_uses_one_probe_and_preserves_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "lean-toolchain").write_text(
        "leanprover/lean4:v4.32.0\n",
        encoding="utf-8",
    )
    first_file = tmp_path / "A" / "B.lean"
    second_file = tmp_path / "C" / "D.lean"
    first_file.parent.mkdir(parents=True)
    second_file.parent.mkdir(parents=True)
    first_file.write_text("theorem t : True := by trivial\n", encoding="utf-8")
    second_file.write_text("def x : Nat := 1\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_assist": {"enabled": True},
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=first_file.resolve().as_uri(),
        diag_timeouts=[],
        verify_diagnostics=[
            {"severity": 3, "message": "'A.B.t' does not depend on any axioms"},
            {
                "severity": 3,
                "message": "'C.D.x' depends on axioms: [Classical.choice]",
            },
        ],
    )
    service = LspAssistServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=fake_client),
    )

    response = service.run_declaration_soundness_batch(
        LspDeclarationSoundnessBatchRequest.from_dict(
            {
                "declarations": [
                    {"file_path": "A/B.lean", "declaration_name": "A.B.t"},
                    {"file_path": "C/D.lean", "declaration_name": "C.D.x"},
                ],
                "scan_source": False,
            }
        )
    )

    assert response.success is True
    assert response.count == 2
    assert response.success_count == 2
    assert response.failure_count == 0
    assert [item.declaration_name for item in response.items] == ["A.B.t", "C.D.x"]
    assert response.items[0].axioms == tuple()
    assert response.items[1].axioms == ("Classical.choice",)
    assert fake_client.diag_timeouts == [15.0]
    assert list(tmp_path.glob("_mcp_decl_soundness_*.lean")) == []


def test_lsp_assist_declaration_soundness_batch_keeps_resolved_partial_results(
    tmp_path: Path,
) -> None:
    (tmp_path / "lean-toolchain").write_text(
        "leanprover/lean4:v4.32.0\n",
        encoding="utf-8",
    )
    target_file = tmp_path / "A" / "B.lean"
    target_file.parent.mkdir(parents=True)
    target_file.write_text(
        "theorem t : True := by trivial\ntheorem missing : True := by trivial\n",
        encoding="utf-8",
    )
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_assist": {"enabled": True},
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=target_file.resolve().as_uri(),
        verify_diagnostics=[
            {"severity": 3, "message": "'A.B.t' does not depend on any axioms"},
            {"severity": 1, "message": "unknown constant 'A.B.missing'"},
        ],
    )
    service = LspAssistServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=fake_client),
    )

    response = service.run_declaration_soundness_batch(
        LspDeclarationSoundnessBatchRequest.from_dict(
            {
                "declarations": [
                    {"file_path": "A/B.lean", "declaration_name": "A.B.t"},
                    {"file_path": "A/B.lean", "declaration_name": "A.B.missing"},
                ],
                "scan_source": False,
            }
        )
    )

    assert response.success is False
    assert response.success_count == 1
    assert response.failure_count == 1
    assert response.items[0].success is True
    assert response.items[1].success is False
    assert "unknown constant" in (response.items[1].error_message or "")


def test_lsp_assist_run_snippet_clamps_timeout_and_recycles_on_failure(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_core": {
                "run_snippet_default_timeout_seconds": 30,
                "run_snippet_max_timeout_seconds": 120,
            },
            "lsp_assist": {
                "enabled": True,
            },
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=tmp_path.resolve().as_uri(),
        diag_error=TimeoutError("timed out"),
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspAssistServiceImpl(config=cfg, lsp_client_manager=manager)

    snippet = service.run_snippet(
        LspRunSnippetRequest.from_dict(
            {
                "code": "import Mathlib\n#check Nat\n",
                "timeout_seconds": 999,
            }
        )
    )

    assert snippet.success is False
    assert "timed out" in (snippet.error_message or "")
    assert fake_client.diag_timeouts == [120.0]
    assert fake_client.closed_paths == []
    assert manager.recycled_roots == [tmp_path.resolve()]
    assert list(tmp_path.glob("_mcp_snippet_*.lean")) == []


def test_lsp_assist_declaration_soundness_recycles_on_failure(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    target_file = tmp_path / "A" / "B.lean"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("theorem t : True := by trivial\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_assist": {"enabled": True},
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=target_file.resolve().as_uri(),
        diag_error=TimeoutError("timed out"),
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspAssistServiceImpl(config=cfg, lsp_client_manager=manager)

    response = service.run_declaration_soundness(
        LspDeclarationSoundnessRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "declaration_name": "A.B.t",
                "scan_source": False,
            }
        )
    )

    assert response.success is False
    assert "timed out" in (response.error_message or "")
    assert fake_client.diag_timeouts == [15.0]
    assert fake_client.closed_paths == []
    assert manager.recycled_roots == [tmp_path.resolve()]
    assert list(tmp_path.glob("_mcp_decl_soundness_*.lean")) == []


def test_lsp_assist_declaration_soundness_hard_timeout_recycles_when_diagnostics_blocks(
    tmp_path: Path,
) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    target_file = tmp_path / "A" / "B.lean"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("theorem t : True := by trivial\n", encoding="utf-8")

    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "backends": {"lsp": {"diagnostics_timeout_seconds": 1}},
            "lsp_assist": {"enabled": True},
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=target_file.resolve().as_uri(),
        diag_delay_seconds=5.0,
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspAssistServiceImpl(config=cfg, lsp_client_manager=manager)

    started = time.monotonic()
    response = service.run_declaration_soundness(
        LspDeclarationSoundnessRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "declaration_name": "A.B.t",
                "scan_source": False,
            }
        )
    )
    elapsed = time.monotonic() - started

    assert response.success is False
    assert "timed out" in (response.error_message or "").lower()
    assert elapsed < 4.0
    assert fake_client.diag_timeouts == [1.0]
    assert fake_client.closed_paths == []
    assert manager.recycled_roots == [tmp_path.resolve()]
    assert list(tmp_path.glob("_mcp_decl_soundness_*.lean")) == []


def test_lsp_assist_run_snippet_hard_timeout_recycles_when_diagnostics_blocks(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_assist"]},
            "lsp_core": {
                "run_snippet_default_timeout_seconds": 1,
                "run_snippet_max_timeout_seconds": 1,
            },
            "lsp_assist": {
                "enabled": True,
            },
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        target_uri=tmp_path.resolve().as_uri(),
        diag_delay_seconds=5.0,
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspAssistServiceImpl(config=cfg, lsp_client_manager=manager)

    started = time.monotonic()
    snippet = service.run_snippet(
        LspRunSnippetRequest.from_dict(
            {
                "code": "import Mathlib\n#check Nat\n",
                "timeout_seconds": 1,
            }
        )
    )
    elapsed = time.monotonic() - started

    assert snippet.success is False
    assert "timed out" in (snippet.error_message or "").lower()
    assert elapsed < 4.0
    assert fake_client.diag_timeouts == [1.0]
    assert fake_client.closed_paths == []
    assert manager.recycled_roots == [tmp_path.resolve()]
    assert list(tmp_path.glob("_mcp_snippet_*.lean")) == []
