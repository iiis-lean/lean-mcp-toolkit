from lean_mcp_toolkit.contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltHammerPremiseResponse,
    ProofSearchAltStateSearchRequest,
    ProofSearchAltStateSearchResponse,
)


def test_proof_search_alt_state_search_contract_roundtrip() -> None:
    req = ProofSearchAltStateSearchRequest.from_dict(
        {"file_path": "Main.lean", "line": 3, "column": 5, "num_results": 4}
    )
    assert req.to_dict()["column"] == 5

    resp = ProofSearchAltStateSearchResponse.from_dict(
        {
            "success": True,
            "provider": "state_search",
            "goal": "⊢ True",
            "backend_mode": "remote",
            "items": [{"name": "True.intro"}],
            "count": 1,
        }
    )
    assert resp.items[0].name == "True.intro"


def test_proof_search_alt_hammer_contract_roundtrip() -> None:
    req = ProofSearchAltHammerPremiseRequest.from_dict(
        {"file_path": "Main.lean", "line": 3, "column": 5, "num_results": 8}
    )
    assert req.to_dict()["num_results"] == 8

    resp = ProofSearchAltHammerPremiseResponse.from_dict(
        {
            "success": True,
            "provider": "hammer_premise",
            "goal": "⊢ True",
            "backend_mode": "remote",
            "items": [{"name": "True.intro"}],
            "count": 1,
        }
    )
    assert resp.items[0].name == "True.intro"

