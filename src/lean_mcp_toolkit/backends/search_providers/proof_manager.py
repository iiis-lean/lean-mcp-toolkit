"""Proof-search backend manager."""

from __future__ import annotations

from dataclasses import dataclass

from ...config import SearchProvidersConfig
from .hammer_premise import HammerPremiseProvider
from .http_common import SearchHttpHelper
from .state_search import StateSearchProvider


@dataclass(slots=True)
class ProofSearchAltBackendManager:
    config: SearchProvidersConfig
    http_helper: SearchHttpHelper
    state_search: StateSearchProvider
    hammer_premise: HammerPremiseProvider

    def __init__(self, *, config: SearchProvidersConfig):
        self.config = config
        self.http_helper = SearchHttpHelper(config=config.http_common)
        self.state_search = StateSearchProvider(config=config.state_search, http_helper=self.http_helper)
        self.hammer_premise = HammerPremiseProvider(
            config=config.hammer_premise,
            http_helper=self.http_helper,
        )

