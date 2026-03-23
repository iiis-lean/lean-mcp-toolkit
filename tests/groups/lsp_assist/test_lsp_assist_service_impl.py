from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_assist import (
    LspCompletionsRequest,
    LspDeclarationFileRequest,
    LspMultiAttemptRequest,
    LspRunSnippetRequest,
    LspTheoremSoundnessRequest,
)
from lean_mcp_toolkit.groups.lsp_assist.service_impl import LspAssistServiceImpl


@dataclass(slots=True)
class _FakeLspClient:
    file_content: str
    target_uri: str

    def open_file(self, rel_path: str, force_reopen: bool = False) -> None:
        _ = rel_path
        _ = force_reopen

    def close_files(self, paths, blocking: bool = True):
        _ = paths
        _ = blocking

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
        _ = start_line, end_line, inactivity_timeout
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
        if rel_path.startswith("_mcp_verify_"):
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

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client


def test_lsp_assist_service_roundtrip(tmp_path: Path) -> None:
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

    soundness = service.run_theorem_soundness(
        LspTheoremSoundnessRequest.from_dict(
            {
                "file_path": "A/B.lean",
                "theorem_name": "A.B.t",
                "scan_source": False,
            }
        )
    )
    assert soundness.success is True
    assert soundness.axiom_count == 1
    assert soundness.axioms == ("Classical.choice",)

