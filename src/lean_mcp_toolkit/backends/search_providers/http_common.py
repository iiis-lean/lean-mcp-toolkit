"""Shared HTTP helpers for external search providers."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from ...config import HttpSearchCommonConfig


class SearchHttpHelper:
    def __init__(self, *, config: HttpSearchCommonConfig):
        self.config = config

    def get_json(
        self,
        *,
        url: str,
        timeout_seconds: int | None,
        headers: dict[str, str] | None = None,
    ):
        req = urllib.request.Request(url=url, headers=self._headers(headers), method="GET")
        return self._execute_json(req=req, timeout_seconds=timeout_seconds)

    def post_json(
        self,
        *,
        url: str,
        payload: object,
        timeout_seconds: int | None,
        headers: dict[str, str] | None = None,
    ):
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers({"Content-Type": "application/json", **(headers or {})}),
            method="POST",
        )
        return self._execute_json(req=req, timeout_seconds=timeout_seconds)

    def get_sse_json(
        self,
        *,
        url: str,
        timeout_seconds: int | None,
        headers: dict[str, str] | None = None,
    ):
        req = urllib.request.Request(
            url=url,
            headers=self._headers({"Accept": "text/event-stream", **(headers or {})}),
            method="GET",
        )
        timeout = timeout_seconds or self.config.default_timeout_seconds
        data_blob: str | None = None
        context = self._ssl_context()
        last_exc: Exception | None = None
        for attempt in range(max(1, 1 + self.config.retry_count)):
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:  # noqa: S310
                    body = resp.read().decode("utf-8", errors="replace")
                for line in body.splitlines():
                    text = line.strip()
                    if not text.startswith("data:"):
                        continue
                    payload = text[5:].strip()
                    if payload:
                        data_blob = payload
                if data_blob is None:
                    raise RuntimeError("SSE response did not contain data event")
                return json.loads(data_blob)
            except Exception as exc:  # pragma: no cover - network boundary
                last_exc = exc
                if attempt < self.config.retry_count and self.config.retry_backoff_seconds > 0:
                    time.sleep(self.config.retry_backoff_seconds)
        raise RuntimeError(f"SSE request failed: {last_exc}") from last_exc

    def _execute_json(self, *, req: urllib.request.Request, timeout_seconds: int | None):
        timeout = timeout_seconds or self.config.default_timeout_seconds
        context = self._ssl_context()
        last_exc: Exception | None = None
        for attempt in range(max(1, 1 + self.config.retry_count)):
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:  # noqa: S310
                    body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body)
            except urllib.error.HTTPError as exc:  # pragma: no cover - network boundary
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    body = str(exc)
                last_exc = RuntimeError(f"http {exc.code}: {body}")
            except Exception as exc:  # pragma: no cover - network boundary
                last_exc = exc
            if attempt < self.config.retry_count and self.config.retry_backoff_seconds > 0:
                time.sleep(self.config.retry_backoff_seconds)
        raise RuntimeError(f"HTTP request failed: {last_exc}") from last_exc

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        headers = {"User-Agent": self.config.user_agent}
        if extra:
            headers.update(extra)
        return headers

    def _ssl_context(self):
        if self.config.verify_ssl:
            return None
        return ssl._create_unverified_context()  # noqa: SLF001


def build_url(base_url: str, path: str, params: dict[str, str] | None = None) -> str:
    root = base_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    url = f"{root}{suffix}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url

