"""Minimal JSON HTTP client wrapper."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from .config import HttpConfig
from .errors import HttpClientError, HttpResponseError


class HttpJsonClient:
    """Small sync HTTP JSON client for service wrappers."""

    def __init__(self, config: HttpConfig):
        if not config.base_url:
            raise ValueError("http base_url is required")
        self.config = config

    def post_json(self, path: str, payload: dict) -> dict:
        return self._request_json("POST", path, payload)

    def get_json(self, path: str) -> dict:
        return self._request_json("GET", path, None)

    def _request_json(self, method: str, path: str, payload: dict | None) -> dict:
        url = self._build_url(path)
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        headers.update(self.config.headers)
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
        context = None
        if not self.config.verify_ssl:
            context = ssl._create_unverified_context()  # noqa: SLF001

        last_exc: Exception | None = None
        total_attempts = max(1, 1 + self.config.retry_count)
        attempts_made = 0
        for attempt_idx in range(total_attempts):
            attempts_made = attempt_idx + 1
            try:
                with urllib.request.urlopen(  # noqa: S310
                    request,
                    timeout=self.config.timeout_seconds,
                    context=context,
                ) as resp:
                    body = resp.read().decode("utf-8")
                    if resp.status < 200 or resp.status >= 300:
                        raise HttpResponseError(status_code=resp.status, body=body)
                    if not body.strip():
                        return {}
                    decoded = json.loads(body)
                    if not isinstance(decoded, dict):
                        raise HttpClientError("expected JSON object response")
                    return decoded
            except HttpResponseError:
                raise
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read().decode("utf-8")
                except Exception:
                    body = str(exc)
                raise HttpResponseError(status_code=exc.code, body=body) from exc
            except Exception as exc:  # pragma: no cover - network boundary
                last_exc = exc

        if attempts_made <= 1:
            raise HttpClientError(f"http request failed: {last_exc}")
        raise HttpClientError(
            f"http request failed after {attempts_made} attempts: {last_exc}"
        )

    def _build_url(self, path: str) -> str:
        prefix = self.config.api_prefix.strip()
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        tool_view = (self.config.tool_view or "").strip()
        if tool_view:
            prefix = f"{prefix}/views/{urllib.parse.quote(tool_view, safe='')}"

        p = path.strip()
        if not p.startswith("/"):
            p = "/" + p

        return f"{self.config.base_url}{prefix}{p}"
