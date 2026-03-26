"""HTTP-adapter payload handlers for build-base tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.build_base import BuildWorkspaceRequest
from ...core.services import BuildBaseService


def handle_build_workspace(service: BuildBaseService, payload: JsonDict) -> JsonDict:
    req = BuildWorkspaceRequest.from_dict(payload)
    resp = service.run_workspace(req)
    return resp.to_dict()
