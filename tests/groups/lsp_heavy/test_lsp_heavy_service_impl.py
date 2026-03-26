from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspWidgetSourceRequest,
    LspWidgetsRequest,
)
from lean_mcp_toolkit.groups.lsp_heavy.service_impl import LspHeavyServiceImpl


@dataclass(slots=True)
class _FakeLspClient:
    def open_file(self, rel_path: str, force_reopen: bool = False) -> None:
        _ = rel_path, force_reopen

    def get_widgets(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return [
            {
                "id": "widget-1",
                "javascriptHash": "abc123",
                "name?": "ProofWidgets.HtmlDisplay",
                "range": {
                    "start": {"line": 1, "character": 2},
                    "end": {"line": 1, "character": 8},
                },
                "props": {"html": "<b>x</b>"},
            }
        ]

    def get_widget_source(self, rel_path: str, line: int, character: int, widget: dict):
        _ = rel_path, line, character, widget
        return {"sourcetext": "console.log('widget')", "module": "foo"}


@dataclass(slots=True)
class _FakeLspClientManager:
    client: _FakeLspClient

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client


def test_lsp_heavy_widgets_and_widget_source(tmp_path: Path) -> None:
    source_file = tmp_path / "Main.lean"
    source_file.write_text("theorem t : True := by\n  trivial\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_heavy"]},
            "lsp_heavy": {"enabled": True, "widget_source_max_chars": 8},
        }
    )
    service = LspHeavyServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=_FakeLspClient()),
    )

    widgets = service.run_widgets(
        LspWidgetsRequest.from_dict({"file_path": "Main.lean", "line": 1, "column": 1})
    )
    assert widgets.success is True
    assert widgets.count == 1
    assert widgets.widgets[0].javascript_hash == "abc123"

    widget_source = service.run_widget_source(
        LspWidgetSourceRequest.from_dict(
            {"file_path": "Main.lean", "javascript_hash": "abc123"}
        )
    )
    assert widget_source.success is True
    assert widget_source.source_text == "console."


def test_lsp_heavy_proof_profile_service(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "Main.lean"
    source_file.write_text("theorem t : True := by\n  trivial\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["lsp_heavy"]},
            "lsp_heavy": {"enabled": True, "proof_profile_default_timeout_seconds": 10},
        }
    )
    service = LspHeavyServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspClientManager(client=_FakeLspClient()),
    )

    class _FakeProfile:
        theorem_name = "t"
        total_ms = 12.3
        lines = tuple()
        categories = tuple()

    monkeypatch.setattr(
        "lean_mcp_toolkit.groups.lsp_heavy.service_impl.profile_theorem",
        lambda **kwargs: _FakeProfile(),
    )

    resp = service.run_proof_profile(
        LspProofProfileRequest.from_dict({"file_path": "Main.lean", "line": 1})
    )
    assert resp.success is True
    assert resp.theorem_name == "t"
    assert resp.total_ms == 12.3

