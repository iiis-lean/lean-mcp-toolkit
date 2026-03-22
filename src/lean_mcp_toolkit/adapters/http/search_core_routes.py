"""HTTP-adapter handlers for search_core tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_core import (
    LocalDeclSearchRequest,
    MathlibDeclGetRequest,
    MathlibDeclSearchRequest,
)
from ...core.services import SearchCoreService


def handle_search_mathlib_decl_search(service: SearchCoreService, payload: JsonDict) -> JsonDict:
    req = MathlibDeclSearchRequest.from_dict(payload)
    resp = service.run_mathlib_decl_search(req)
    return resp.to_dict()


def handle_search_mathlib_decl_get(service: SearchCoreService, payload: JsonDict) -> JsonDict:
    req = MathlibDeclGetRequest.from_dict(payload)
    resp = service.run_mathlib_decl_get(req)
    return resp.to_dict()


def handle_search_local_decl_search(service: SearchCoreService, payload: JsonDict) -> JsonDict:
    req = LocalDeclSearchRequest.from_dict(payload)
    resp = service.run_local_decl_search(req)
    return resp.to_dict()
