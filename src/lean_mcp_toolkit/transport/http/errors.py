"""HTTP transport exceptions."""

from __future__ import annotations


class HttpClientError(RuntimeError):
    """Base HTTP client error."""


class HttpResponseError(HttpClientError):
    """Raised when server returns non-2xx status."""

    def __init__(self, *, status_code: int, body: str):
        super().__init__(f"http response error: status={status_code}, body={body}")
        self.status_code = status_code
        self.body = body
