from lean_mcp_toolkit.contracts.search_alt import (
    SearchAltLeanDexRequest,
    SearchAltLeanDexResponse,
    SearchAltLeanSearchRequest,
    SearchAltLeanSearchResponse,
)


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

