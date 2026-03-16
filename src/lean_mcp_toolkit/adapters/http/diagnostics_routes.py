"""HTTP-adapter payload handlers for diagnostics tools.

These handlers only perform contract parsing/serialization.
Actual execution belongs to the injected service implementation.
"""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.diagnostics import BuildRequest, LintRequest
from ...core.services import DiagnosticsService



def handle_diagnostics_build(service: DiagnosticsService, payload: JsonDict) -> JsonDict:
    req = BuildRequest.from_dict(payload)
    resp = service.run_build(req)
    return resp.to_dict()



def handle_diagnostics_lint(service: DiagnosticsService, payload: JsonDict) -> JsonDict:
    req = LintRequest.from_dict(payload)
    resp = service.run_lint(req)
    return resp.to_dict()



def handle_diagnostics_lint_no_sorry(service: DiagnosticsService, payload: JsonDict) -> JsonDict:
    req = LintRequest.from_dict(payload)
    resp = service.run_lint_no_sorry(req)
    return resp.to_dict()
