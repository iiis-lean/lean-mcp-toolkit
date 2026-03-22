"""HTTP-adapter payload handlers for declarations tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.declarations import DeclarationExtractRequest, DeclarationLocateRequest
from ...core.services import DeclarationsService


def handle_declarations_extract(service: DeclarationsService, payload: JsonDict) -> JsonDict:
    req = DeclarationExtractRequest.from_dict(payload)
    resp = service.extract(req)
    return resp.to_dict()


def handle_declarations_locate(service: DeclarationsService, payload: JsonDict) -> JsonDict:
    req = DeclarationLocateRequest.from_dict(payload)
    resp = service.locate(req)
    return resp.to_dict()
