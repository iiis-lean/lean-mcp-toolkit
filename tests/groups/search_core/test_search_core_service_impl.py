from dataclasses import dataclass

from lean_mcp_toolkit.backends.lean_explore import LeanExploreRecord, LeanExploreSearchResult
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclGetRequest,
)
from lean_mcp_toolkit.groups.search_core.service_impl import SearchCoreServiceImpl


@dataclass(slots=True)
class _FakeLeanExploreBackend:
    items: tuple[LeanExploreRecord, ...]

    def search(
        self,
        *,
        query: str,
        limit: int,
        rerank_top: int | None,
        packages: tuple[str, ...] | None,
    ) -> LeanExploreSearchResult:
        _ = limit, rerank_top, packages
        return LeanExploreSearchResult(query=query, processing_time_ms=7, items=self.items)

    def get_by_id(self, declaration_id: int) -> LeanExploreRecord | None:
        for item in self.items:
            if item.id == declaration_id:
                return item
        return None



def test_search_core_service_mathlib_find_and_get() -> None:
    cfg = ToolkitConfig()
    item = LeanExploreRecord(
        id=1,
        name="Nat.succ",
        module="Mathlib.Init",
        docstring="doc",
        source_text="def succ",
        source_link="https://example.com",
        dependencies="[]",
        informalization="succ",
    )
    svc = SearchCoreServiceImpl(
        config=cfg,
        lean_explore_backend=_FakeLeanExploreBackend(items=(item,)),
    )

    search_resp = svc.run_mathlib_decl_find(
        MathlibDeclFindRequest.from_dict(
            {
                "query": "succ",
                "include_module": True,
                "include_docstring": True,
                "include_source_text": False,
                "include_source_link": False,
                "include_dependencies": False,
                "include_informalization": False,
            }
        )
    )
    assert search_resp.count == 1
    assert search_resp.results[0].name == "Nat.succ"
    assert search_resp.results[0].module == "Mathlib.Init"
    assert search_resp.results[0].source_text is None

    get_resp = svc.run_mathlib_decl_get(
        MathlibDeclGetRequest.from_dict({"declaration_id": 1, "include_source_text": True})
    )
    assert get_resp.found is True
    assert get_resp.item is not None
    assert get_resp.item.source_text == "def succ"
