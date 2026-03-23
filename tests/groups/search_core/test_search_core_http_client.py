from dataclasses import dataclass

from lean_mcp_toolkit.contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclGetRequest,
)
from lean_mcp_toolkit.groups.search_core.client_http import SearchCoreHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        _ = payload
        if path == "/search/mathlib_decl/find":
            return {
                "query": "Nat",
                "count": 1,
                "results": [{"id": 1, "name": "Nat.succ"}],
            }
        if path == "/search/mathlib_decl/get":
            return {
                "found": True,
                "item": {"id": 1, "name": "Nat.succ"},
            }
        raise AssertionError(f"unexpected path: {path}")



def test_search_core_http_client_roundtrip() -> None:
    client = SearchCoreHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=_FakeHttpJsonClient(),
    )

    search_resp = client.run_mathlib_decl_find(MathlibDeclFindRequest.from_dict({"query": "Nat"}))
    assert search_resp.count == 1
    assert search_resp.results[0].name == "Nat.succ"

    get_resp = client.run_mathlib_decl_get(MathlibDeclGetRequest.from_dict({"declaration_id": 1}))
    assert get_resp.found is True
    assert get_resp.item is not None
    assert get_resp.item.name == "Nat.succ"
