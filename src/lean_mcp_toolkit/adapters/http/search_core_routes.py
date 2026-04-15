"""HTTP-adapter handlers for search_core tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_core import (
    MathlibDeclFindRequest,
    MathlibDeclGetRequest,
)
from ...core.services import SearchCoreService


def handle_search_mathlib_decl_find(service: SearchCoreService, payload: JsonDict) -> JsonDict:
    req = MathlibDeclFindRequest.from_dict(payload)
    resp = service.run_mathlib_decl_find(req)
    return resp


def handle_search_mathlib_decl_get(service: SearchCoreService, payload: JsonDict) -> JsonDict:
    req = MathlibDeclGetRequest.from_dict(payload)
    resp = service.run_mathlib_decl_get(req)
    return resp

__all__ = ["handle_search_mathlib_decl_find", "handle_search_mathlib_decl_get"]
