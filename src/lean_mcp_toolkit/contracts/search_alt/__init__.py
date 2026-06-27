"""Contracts for search_alt tools."""

from .arxiv_theorems import (
    ArxivTheoremItem,
    SearchAltArxivTheoremsRequest,
    SearchAltArxivTheoremsResponse,
)
from .common import SearchAltRequest
from .leandex import LeanDexItem, SearchAltLeanDexRequest, SearchAltLeanDexResponse
from .leanfinder import (
    LeanFinderItem,
    SearchAltLeanFinderRequest,
    SearchAltLeanFinderResponse,
)
from .leansearch import (
    LeanSearchItem,
    SearchAltLeanSearchRequest,
    SearchAltLeanSearchResponse,
)
from .loogle import LoogleItem, SearchAltLoogleRequest, SearchAltLoogleResponse

__all__ = [
    "SearchAltRequest",
    "SearchAltArxivTheoremsRequest",
    "ArxivTheoremItem",
    "SearchAltArxivTheoremsResponse",
    "SearchAltLeanSearchRequest",
    "LeanSearchItem",
    "SearchAltLeanSearchResponse",
    "SearchAltLeanDexRequest",
    "LeanDexItem",
    "SearchAltLeanDexResponse",
    "SearchAltLoogleRequest",
    "LoogleItem",
    "SearchAltLoogleResponse",
    "SearchAltLeanFinderRequest",
    "LeanFinderItem",
    "SearchAltLeanFinderResponse",
]
