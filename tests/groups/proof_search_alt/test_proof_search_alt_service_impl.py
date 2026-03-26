from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltStateSearchRequest,
)
from lean_mcp_toolkit.groups.proof_search_alt.service_impl import ProofSearchAltServiceImpl


@dataclass(slots=True)
class _FakeLspClient:
    def open_file(self, rel_path: str, force_reopen: bool = False) -> None:
        _ = rel_path, force_reopen

    def get_goal(self, rel_path: str, line: int, character: int):
        _ = rel_path, line, character
        return {"goals": ["⊢ True"]}


@dataclass(slots=True)
class _FakeLspManager:
    client: _FakeLspClient

    def get_client(self, project_root: Path):
        _ = project_root
        return self.client


@dataclass(slots=True)
class _FakeStateSearch:
    def search(self, *, goal: str, num_results: int, include_raw_payload: bool):
        _ = goal, num_results, include_raw_payload
        return [{"name": "True.intro"}]


@dataclass(slots=True)
class _FakeHammer:
    def search(self, *, goal: str, num_results: int, include_raw_payload: bool):
        _ = goal, num_results, include_raw_payload
        return [{"name": "True.intro"}]


@dataclass(slots=True)
class _FakeProofManager:
    config: object
    state_search: _FakeStateSearch
    hammer_premise: _FakeHammer


def test_proof_search_alt_service_roundtrip(tmp_path: Path) -> None:
    source_file = tmp_path / "Main.lean"
    source_file.write_text("theorem t : True := by\n  trivial\n", encoding="utf-8")
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "groups": {"enabled_groups": ["proof_search_alt"]},
            "proof_search_alt": {"enabled": True},
        }
    )
    service = ProofSearchAltServiceImpl(
        config=cfg,
        lsp_client_manager=_FakeLspManager(client=_FakeLspClient()),
        backend_manager=_FakeProofManager(
            config=cfg.backends.search_providers,
            state_search=_FakeStateSearch(),
            hammer_premise=_FakeHammer(),
        ),
    )

    state = service.run_state_search(
        ProofSearchAltStateSearchRequest(file_path="Main.lean", line=1, column=1)
    )
    hammer = service.run_hammer_premise(
        ProofSearchAltHammerPremiseRequest(file_path="Main.lean", line=1, column=1)
    )

    assert state.success is True
    assert state.goal == "⊢ True"
    assert hammer.items[0].name == "True.intro"

