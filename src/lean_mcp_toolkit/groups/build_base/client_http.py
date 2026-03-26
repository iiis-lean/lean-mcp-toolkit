"""HTTP-backed build_base client implementing BuildBaseService protocol."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.build_base import BuildWorkspaceRequest, BuildWorkspaceResponse
from ...core.services import BuildBaseService
from ...transport.http import HttpConfig, HttpJsonClient


class BuildBaseHttpClient(BuildBaseService):
    """Build-base service-compatible HTTP client."""

    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_workspace(self, req: BuildWorkspaceRequest) -> BuildWorkspaceResponse:
        data = self._post("/build/workspace", req.to_dict())
        return BuildWorkspaceResponse.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)
