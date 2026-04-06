from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_core import (
    LspCodeActionsRequest,
    LspFileOutlineRequest,
    LspGoalRequest,
    LspHoverRequest,
    MarkdownResponse,
)
from lean_mcp_toolkit.contracts.lsp_assist import LspRunSnippetRequest
from lean_mcp_toolkit.groups.lsp_core.service_impl import LspCoreServiceImpl


@dataclass(slots=True)
class _DiagResult:
    success: bool
    diagnostics: list[dict]


@dataclass(slots=True)
class _FakeLspClient:
    file_content: str

    def open_file(self, rel_path: str) -> None:
        _ = rel_path

    def close_files(self, rel_paths: list[str]) -> None:
        _ = rel_paths

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
        _ = rel_path, start_line, end_line, inactivity_timeout
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

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client



def test_lsp_core_service_structured_and_markdown(tmp_path: Path) -> None:
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
    assert not isinstance(outline, MarkdownResponse)
    assert outline.success is True
    assert outline.imports == ("Mathlib",)
    assert len(outline.declarations) == 1

    goals = service.run_goal(LspGoalRequest.from_dict({"file_path": "A/B.lean", "line": 3}))
    assert not isinstance(goals, MarkdownResponse)
    assert goals.success is True
    assert goals.goals_before == ("⊢ True",)

    hover_md = service.run_hover(
        LspHoverRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "line": 3,
                "column": 9,
                "response_format": "markdown",
            }
        )
    )
    assert isinstance(hover_md, MarkdownResponse)
    assert "Hover" in hover_md.markdown

    actions = service.run_code_actions(
        LspCodeActionsRequest.from_dict({"file_path": "A/B.lean", "line": 3})
    )
    assert not isinstance(actions, MarkdownResponse)
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
    assert not isinstance(outline_from_nested_root, MarkdownResponse)
    assert outline_from_nested_root.success is True
