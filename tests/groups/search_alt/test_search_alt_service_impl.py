from dataclasses import dataclass

from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.search_alt import (
    SearchAltLeanDexRequest,
    SearchAltLeanFinderRequest,
    SearchAltLeanSearchRequest,
    SearchAltLoogleRequest,
)
from lean_mcp_toolkit.groups.search_alt.service_impl import SearchAltServiceImpl


@dataclass(slots=True)
class _FakeLeansearch:
    def search(self, *, query: str, num_results: int, include_raw_payload: bool):
        _ = query, num_results, include_raw_payload
        return [{"name": "Nat.succ", "module_name": "Init.Prelude"}]


@dataclass(slots=True)
class _FakeLeandex:
    def search(self, *, query: str, num_results: int, include_raw_payload: bool):
        _ = query, num_results, include_raw_payload
        return [{"primary_declaration": "Nat.succ_ne_self"}]


@dataclass(slots=True)
class _FakeLeanfinder:
    def search(self, *, query: str, num_results: int, include_raw_payload: bool):
        _ = query, num_results, include_raw_payload
        return [
            {
                "full_name": "Nat.succ_ne_self",
                "formal_statement": "theorem ...",
                "informal_statement": "succ is not self",
            }
        ]


@dataclass(slots=True)
class _FakeManager:
    config: object
    leansearch: _FakeLeansearch
    leandex: _FakeLeandex
    leanfinder: _FakeLeanfinder

    def search_loogle(self, *, query: str, num_results: int, include_raw_payload: bool, project_root):
        _ = query, num_results, include_raw_payload, project_root
        return ("local", [{"name": "Nat.succ", "type": "Nat -> Nat", "module": "Init.Prelude"}])


def test_search_alt_service_roundtrip() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {"enabled_groups": ["search_alt"]},
            "search_alt": {"enabled": True},
        }
    )
    manager = _FakeManager(
        config=cfg.backends.search_providers,
        leansearch=_FakeLeansearch(),
        leandex=_FakeLeandex(),
        leanfinder=_FakeLeanfinder(),
    )
    service = SearchAltServiceImpl(config=cfg, backend_manager=manager)

    leansearch = service.run_leansearch(SearchAltLeanSearchRequest(query="Nat.succ"))
    leandex = service.run_leandex(SearchAltLeanDexRequest(query="succ"))
    loogle = service.run_loogle(SearchAltLoogleRequest(query="Nat -> Nat"))
    leanfinder = service.run_leanfinder(SearchAltLeanFinderRequest(query="succ is not self"))

    assert leansearch.success is True
    assert leansearch.items[0].name == "Nat.succ"
    assert leandex.items[0].primary_declaration == "Nat.succ_ne_self"
    assert loogle.backend_mode == "local"
    assert leanfinder.items[0].full_name == "Nat.succ_ne_self"

