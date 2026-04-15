"""HTTP-adapter handlers for mathlib_nav tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavGrepRequest,
    MathlibNavReadRequest,
    MathlibNavTreeRequest,
)
from ...core.services import MathlibNavService


def handle_search_mathlib_nav_tree(service: MathlibNavService, payload: JsonDict) -> JsonDict:
    req = MathlibNavTreeRequest.from_dict(payload)
    return service.run_mathlib_nav_tree(req)


def handle_search_mathlib_nav_file_outline(
    service: MathlibNavService,
    payload: JsonDict,
) -> JsonDict:
    req = MathlibNavFileOutlineRequest.from_dict(payload)
    return service.run_mathlib_nav_file_outline(req)


def handle_search_mathlib_nav_grep(service: MathlibNavService, payload: JsonDict) -> JsonDict:
    req = MathlibNavGrepRequest.from_dict(payload)
    return service.run_mathlib_nav_grep(req)


def handle_search_mathlib_nav_read(service: MathlibNavService, payload: JsonDict) -> JsonDict:
    req = MathlibNavReadRequest.from_dict(payload)
    return service.run_mathlib_nav_read(req)


__all__ = [
    "handle_search_mathlib_nav_tree",
    "handle_search_mathlib_nav_file_outline",
    "handle_search_mathlib_nav_grep",
    "handle_search_mathlib_nav_read",
]
