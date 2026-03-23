"""HTTP-backed diagnostics client implementing DiagnosticsService protocol."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.diagnostics import (
    AxiomAuditResult,
    BuildRequest,
    BuildResponse,
    FileRequest,
    FileResponse,
    LintRequest,
    LintResponse,
    NoSorryResult,
)
from ...core.services import DiagnosticsService
from ...transport.http import HttpConfig, HttpJsonClient


class DiagnosticsHttpClient(DiagnosticsService):
    """Diagnostics service-compatible HTTP client."""

    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_build(self, req: BuildRequest) -> BuildResponse:
        payload = req.to_dict()
        data = self._post("/diagnostics/build", payload)
        return BuildResponse.from_dict(data)

    def run_file(self, req: FileRequest) -> FileResponse:
        payload = req.to_dict()
        data = self._post("/diagnostics/file", payload)
        return FileResponse.from_dict(data)

    def run_lint(self, req: LintRequest) -> LintResponse:
        payload = req.to_dict()
        data = self._post("/diagnostics/lint", payload)
        return LintResponse.from_dict(data)

    def run_lint_no_sorry(self, req: LintRequest) -> NoSorryResult:
        payload = req.to_dict()
        data = self._post("/diagnostics/lint/no_sorry", payload)
        return NoSorryResult.from_dict(data)

    def run_lint_axiom_audit(self, req: LintRequest) -> AxiomAuditResult:
        payload = req.to_dict()
        data = self._post("/diagnostics/lint/axiom_audit", payload)
        return AxiomAuditResult.from_dict(data)

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        result = self.http_client.post_json(path, payload)
        return result
