from lean_mcp_toolkit.contracts.search_alt import (
    SearchAltLeanSearchRequest,
    SearchAltLoogleRequest,
)
from lean_mcp_toolkit.groups.search_alt.client_http import SearchAltHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


class _FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post_json(self, path: str, payload: dict) -> dict:
        self.calls.append((path, payload))
        return {
            "success": True,
            "query": payload.get("query", ""),
            "provider": "x",
            "backend_mode": "remote",
            "items": [],
            "count": 0,
        }


def test_search_alt_http_client_roundtrip() -> None:
    http = _FakeHttpClient()
    client = SearchAltHttpClient(
        http_config=HttpConfig(base_url="http://example.com"),
        http_client=http,
    )
    client.run_leansearch(SearchAltLeanSearchRequest(query="Nat.succ"))
    client.run_loogle(SearchAltLoogleRequest(query="Nat -> Nat"))
    assert [path for path, _ in http.calls] == [
        "/search_alt/leansearch",
        "/search_alt/loogle",
    ]

