"""HTTP-adapter payload handlers for search_alt tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_alt import (
    SearchAltArxivTheoremsRequest,
    SearchAltLeanDexRequest,
    SearchAltLeanFinderRequest,
    SearchAltLeanSearchRequest,
    SearchAltLoogleRequest,
)
from ...core.services import SearchAltService


def handle_search_alt_arxiv_theorems(service: SearchAltService, payload: JsonDict) -> JsonDict:
    return service.run_arxiv_theorems(SearchAltArxivTheoremsRequest.from_dict(payload))


def handle_search_alt_leansearch(service: SearchAltService, payload: JsonDict) -> JsonDict:
    return service.run_leansearch(SearchAltLeanSearchRequest.from_dict(payload))


def handle_search_alt_leandex(service: SearchAltService, payload: JsonDict) -> JsonDict:
    return service.run_leandex(SearchAltLeanDexRequest.from_dict(payload))


def handle_search_alt_loogle(service: SearchAltService, payload: JsonDict) -> JsonDict:
    return service.run_loogle(SearchAltLoogleRequest.from_dict(payload))


def handle_search_alt_leanfinder(service: SearchAltService, payload: JsonDict) -> JsonDict:
    return service.run_leanfinder(SearchAltLeanFinderRequest.from_dict(payload))
