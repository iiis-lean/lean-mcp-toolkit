"""HTTP-adapter payload handlers for proof_search_alt tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltStateSearchRequest,
)
from ...core.services import ProofSearchAltService


def handle_proof_search_alt_state_search(
    service: ProofSearchAltService,
    payload: JsonDict,
) -> JsonDict:
    return service.run_state_search(ProofSearchAltStateSearchRequest.from_dict(payload)).to_dict()


def handle_proof_search_alt_hammer_premise(
    service: ProofSearchAltService,
    payload: JsonDict,
) -> JsonDict:
    return service.run_hammer_premise(
        ProofSearchAltHammerPremiseRequest.from_dict(payload)
    ).to_dict()
