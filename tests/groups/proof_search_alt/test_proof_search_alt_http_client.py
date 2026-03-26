from lean_mcp_toolkit.contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltStateSearchRequest,
)
from lean_mcp_toolkit.groups.proof_search_alt.client_http import ProofSearchAltHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


class _FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post_json(self, path: str, payload: dict) -> dict:
        self.calls.append((path, payload))
        return {
            "success": True,
            "provider": "x",
            "goal": "⊢ True",
            "backend_mode": "remote",
            "items": [],
            "count": 0,
        }


def test_proof_search_alt_http_client_roundtrip() -> None:
    http = _FakeHttpClient()
    client = ProofSearchAltHttpClient(
        http_config=HttpConfig(base_url="http://example.com"),
        http_client=http,
    )
    client.run_state_search(ProofSearchAltStateSearchRequest(file_path="Main.lean", line=1, column=1))
    client.run_hammer_premise(
        ProofSearchAltHammerPremiseRequest(file_path="Main.lean", line=1, column=1)
    )
    assert [path for path, _ in http.calls] == [
        "/proof_search_alt/state_search",
        "/proof_search_alt/hammer_premise",
    ]
