"""HTTP-backed proof_search_alt client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.proof_search_alt import (
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltHammerPremiseResponse,
    ProofSearchAltStateSearchRequest,
    ProofSearchAltStateSearchResponse,
)
from ...core.services import ProofSearchAltService
from ...transport.http import HttpConfig, HttpJsonClient


class ProofSearchAltHttpClient(ProofSearchAltService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_state_search(
        self,
        req: ProofSearchAltStateSearchRequest,
    ) -> ProofSearchAltStateSearchResponse:
        return ProofSearchAltStateSearchResponse.from_dict(
            self._post("/proof_search_alt/state_search", req.to_dict())
        )

    def run_hammer_premise(
        self,
        req: ProofSearchAltHammerPremiseRequest,
    ) -> ProofSearchAltHammerPremiseResponse:
        return ProofSearchAltHammerPremiseResponse.from_dict(
            self._post("/proof_search_alt/hammer_premise", req.to_dict())
        )

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["ProofSearchAltHttpClient"]

