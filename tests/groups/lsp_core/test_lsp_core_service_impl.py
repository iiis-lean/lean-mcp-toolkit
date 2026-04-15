from dataclasses import dataclass
from pathlib import Path
import time

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_core import (
    LspCodeActionsRequest,
    LspFileOutlineRequest,
    LspGoalRequest,
    LspHoverRequest,
    LspRunSnippetRequest,
)
from lean_mcp_toolkit.groups.lsp_core.service_impl import LspCoreServiceImpl


@dataclass(slots=True)
class _DiagResult:
    success: bool
    diagnostics: list[dict]


@dataclass(slots=True)
class _FakeLspClient:
    file_content: str
    diag_error: Exception | None = None
    diag_delay_seconds: float = 0.0
    diag_timeouts: list[float] | None = None
    closed_paths: list[list[str]] | None = None

    def open_file(self, rel_path: str) -> None:
        _ = rel_path

    def close_files(self, rel_paths: list[str]) -> None:
        if self.closed_paths is not None:
            self.closed_paths.append(list(rel_paths))

    def get_file_content(self, rel_path: str) -> str:
        _ = rel_path
        return self.file_content

    def get_document_symbols(self, rel_path: str):
        _ = rel_path
        return [
            {
                "name": "A.foo",
                "kind": "theorem",
                "range": {
                    "start": {"line": 2, "character": 0},
                    "end": {"line": 3, "character": 10},
                },
                "children": [],
            }
        ]

    def get_goal(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return {"goals": ["⊢ True"]}

    def get_term_goal(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return {"goal": "```lean\n⊢ True\n```"}

    def get_hover(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return {
            "range": {
                "start": {"line": 2, "character": 8},
                "end": {"line": 2, "character": 11},
            },
            "contents": {"value": "```lean\nA.foo : True\n```"},
        }

    def get_diagnostics(
        self,
        rel_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        inactivity_timeout: float = 15.0,
    ) -> _DiagResult:
        _ = rel_path, start_line, end_line
        if self.diag_timeouts is not None:
            self.diag_timeouts.append(inactivity_timeout)
        if self.diag_delay_seconds > 0:
            time.sleep(self.diag_delay_seconds)
        if self.diag_error is not None:
            raise self.diag_error
        return _DiagResult(
            success=True,
            diagnostics=[
                {
                    "severity": 2,
                    "message": "unused",
                    "fullRange": {
                        "start": {"line": 2, "character": 8},
                        "end": {"line": 2, "character": 11},
                    },
                }
            ],
        )

    def get_code_actions(
        self,
        rel_path: str,
        start_line: int,
        start_character: int,
        end_line: int,
        end_character: int,
    ):
        _ = rel_path, start_line, start_character, end_line, end_character
        return [{"title": "Try this", "isPreferred": True}]

    def get_code_action_resolve(self, action: dict):
        _ = action
        return {
            "title": "Try this",
            "isPreferred": True,
            "edit": {
                "documentChanges": [
                    {
                        "edits": [
                            {
                                "newText": "exact trivial",
                                "range": {
                                    "start": {"line": 2, "character": 2},
                                    "end": {"line": 2, "character": 8},
                                },
                            }
                        ]
                    }
                ]
            },
        }


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



def test_lsp_core_service_returns_structured_responses(tmp_path: Path) -> None:
    content = "import Mathlib\n\n theorem foo : True := by\n  trivial\n"
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    file_path = tmp_path / "A" / "B.lean"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    service = LspCoreServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=_FakeLspClient(file_content=content)),
    )

    outline = service.run_file_outline(
        LspFileOutlineRequest.from_dict({"file_path": "A/B.lean"})
    )
    assert outline.success is True
    assert outline.imports == ("Mathlib",)
    assert len(outline.declarations) == 1

    goals = service.run_goal(LspGoalRequest.from_dict({"file_path": "A/B.lean", "line": 3}))
    assert goals.success is True
    assert goals.goals_before == ("⊢ True",)

    hover = service.run_hover(
        LspHoverRequest.from_dict({"file_path": "A/B.lean", "line": 3, "column": 9})
    )
    assert hover.success is True
    assert hover.info is not None

    actions = service.run_code_actions(
        LspCodeActionsRequest.from_dict({"file_path": "A/B.lean", "line": 3})
    )
    assert actions.success is True
    assert len(actions.actions) == 1
    assert actions.actions[0].title == "Try this"
    assert actions.actions[0].edits[0].new_text == "exact trivial"

    snippet = service.run_snippet(
        LspRunSnippetRequest.from_dict({"code": "import Mathlib\ndef x := 1\n"})
    )
    assert snippet.success is True
    assert snippet.warning_count == 1

    outline_from_nested_root = service.run_file_outline(
        LspFileOutlineRequest.from_dict(
            {
                "project_root": str(tmp_path / "A"),
                "file_path": "A/B.lean",
            }
        )
    )
    assert outline_from_nested_root.success is True


def test_lsp_core_run_snippet_clamps_timeout_and_recycles_on_failure(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "lsp_core": {
                "run_snippet_default_timeout_seconds": 30,
                "run_snippet_max_timeout_seconds": 120,
            },
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        diag_error=TimeoutError("timed out"),
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspCoreServiceImpl(config=cfg, lsp_client_manager=manager)

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


def test_lsp_core_run_snippet_hard_timeout_recycles_when_diagnostics_blocks(tmp_path: Path) -> None:
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "lsp_core": {
                "run_snippet_default_timeout_seconds": 1,
                "run_snippet_max_timeout_seconds": 1,
            },
        }
    )
    fake_client = _FakeLspClient(
        file_content="",
        diag_delay_seconds=5.0,
        diag_timeouts=[],
        closed_paths=[],
    )
    manager = _FakeLspClientManager(client=fake_client, recycled_roots=[])
    service = LspCoreServiceImpl(config=cfg, lsp_client_manager=manager)

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
