from lean_mcp_toolkit.contracts.search_alt import (
    SearchAltArxivTheoremsRequest,
    SearchAltArxivTheoremsResponse,
    SearchAltLeanDexRequest,
    SearchAltLeanDexResponse,
    SearchAltLeanSearchRequest,
    SearchAltLeanSearchResponse,
)


def test_search_alt_arxiv_theorems_contract_roundtrip() -> None:
    req = SearchAltArxivTheoremsRequest.from_dict(
        {"query": "compactness theorem", "num_results": 4}
    )
    assert req.to_dict()["query"] == "compactness theorem"
    assert req.to_dict()["num_results"] == 4

    resp = SearchAltArxivTheoremsResponse.from_dict(
        {
            "success": True,
            "query": "compactness theorem",
            "provider": "arxiv_theorems",
            "backend_mode": "remote",
            "items": [
                {
                    "title": "A compactness paper",
                    "theorem": "Every open cover has a finite subcover.",
                    "arxiv_id": "2401.01234",
                    "theorem_id": "thm:compact",
                }
            ],
            "count": 1,
        }
    )
    assert resp.success is True
    assert resp.items[0].theorem_id == "thm:compact"


def test_search_alt_leansearch_contract_roundtrip() -> None:
    req = SearchAltLeanSearchRequest.from_dict({"query": "Nat.succ", "num_results": 3})
    assert req.to_dict()["num_results"] == 3

    resp = SearchAltLeanSearchResponse.from_dict(
        {
            "success": True,
            "query": "Nat.succ",
            "provider": "leansearch",
            "backend_mode": "remote",
            "items": [{"name": "Nat.succ", "module_name": "Init.Prelude"}],
            "count": 1,
        }
    )
    assert resp.success is True
    assert resp.items[0].name == "Nat.succ"


def test_search_alt_leandex_contract_roundtrip() -> None:
    req = SearchAltLeanDexRequest.from_dict({"query": "succ", "num_results": 2})
    assert req.to_dict()["query"] == "succ"

    resp = SearchAltLeanDexResponse.from_dict(
        {
            "success": True,
            "query": "succ",
            "provider": "leandex",
            "backend_mode": "remote",
            "items": [{"primary_declaration": "Nat.succ_ne_self"}],
            "count": 1,
        }
    )
    assert resp.items[0].primary_declaration == "Nat.succ_ne_self"
