from __future__ import annotations

from contextlib import contextmanager
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest

from lean_mcp_toolkit.backends.lean_explore.api_backend import LeanExploreApiBackend
from lean_mcp_toolkit.config import LeanExploreBackendConfig, SearchCoreConfig


@contextmanager
def _remote_server(
    *,
    lean_version: str = "4.32.0",
    fail_search_attempts: int = 0,
) -> Iterator[tuple[str, list[dict[str, object]]]]:
    requests: list[dict[str, object]] = []
    remaining_failures = {"search": fail_search_attempts}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            requests.append(
                {
                    "path": parsed.path,
                    "query": parse_qs(parsed.query),
                    "authorization": self.headers.get("Authorization"),
                }
            )
            if parsed.path == "/api/v2/health":
                self._send(
                    200,
                    {
                        "status": "ready",
                        "index_id": "20260714_172516",
                        "lean_version": lean_version,
                        "mathlib_revision": "aae61ae",
                    },
                )
                return
            if parsed.path == "/api/v2/search":
                if remaining_failures["search"] > 0:
                    remaining_failures["search"] -= 1
                    self._send(503, {"detail": "warming"})
                    return
                self._send(
                    200,
                    {
                        "query": parse_qs(parsed.query).get("q", [""])[0],
                        "processing_time_ms": 4,
                        "results": [_record_payload()],
                    },
                )
                return
            if parsed.path == "/api/v2/declarations/7":
                self._send(200, _record_payload())
                return
            if parsed.path.startswith("/api/v2/declarations/"):
                self._send(404, {"detail": "not found"})
                return
            self._send(404, {"detail": "not found"})

        def _send(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api/v2", requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _record_payload() -> dict[str, object]:
    return {
        "id": 7,
        "name": "Nat.succ",
        "module": "Mathlib.Data.Nat.Basic",
        "docstring": None,
        "source_text": "def Nat.succ",
        "source_link": "https://example.invalid/Nat.lean",
        "dependencies": None,
        "informalization": "successor",
    }


def _backend(base_url: str, *, lean_version: str = "4.32.0", **overrides: object):
    config_values: dict[str, object] = {
        "mode": "api",
        "api_base_url": base_url,
        "api_key_env": "LEANEXPLORE_TEST_KEY",
        "api_verify_on_startup": True,
        "api_trust_env": False,
    }
    config_values.update(overrides)
    return LeanExploreApiBackend(
        backend_config=LeanExploreBackendConfig(**config_values),
        search_config=SearchCoreConfig(mathlib_lean_version=lean_version),
    )


def test_api_backend_search_get_and_metadata_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    with _remote_server() as (base_url, requests):
        backend = _backend(base_url)

        result = backend.search(
            query="successor",
            limit=3,
            rerank_top=50,
            packages=("Mathlib",),
        )
        item = backend.get_by_id(7)
        missing = backend.get_by_id(999)

    assert result.query == "successor"
    assert result.processing_time_ms == 4
    assert result.items[0].name == "Nat.succ"
    assert item is not None and item.id == 7
    assert missing is None
    assert [request["path"] for request in requests] == [
        "/api/v2/health",
        "/api/v2/search",
        "/api/v2/declarations/7",
        "/api/v2/declarations/999",
    ]
    assert requests[1]["query"] == {
        "q": ["successor"],
        "limit": ["3"],
        "rerank_top": ["50"],
        "packages": ["Mathlib"],
    }
    assert all(request["authorization"] == "Bearer test-secret" for request in requests)


def test_api_backend_startup_validation_eagerly_checks_remote_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    with _remote_server() as (base_url, requests):
        backend = _backend(base_url)

        backend.validate_startup()
        result = backend.search(query="Nat", limit=1, rerank_top=0, packages=None)

    assert result.items[0].name == "Nat.succ"
    assert [request["path"] for request in requests] == [
        "/api/v2/health",
        "/api/v2/search",
    ]


def test_api_backend_rejects_remote_lean_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    with _remote_server(lean_version="4.28.0") as (base_url, _requests):
        backend = _backend(base_url, lean_version="4.32.0")
        with pytest.raises(RuntimeError, match="expected 4.32.0, got 4.28.0"):
            backend.search(query="Nat", limit=1, rerank_top=0, packages=("Mathlib",))


def test_api_backend_startup_validation_rejects_unreachable_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    backend = _backend(
        "http://127.0.0.1:1/api/v2",
        api_timeout_seconds=1,
        api_retry_count=0,
    )

    with pytest.raises(RuntimeError, match="remote LeanExplore request failed"):
        backend.validate_startup()


def test_api_backend_retries_retryable_http_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEANEXPLORE_TEST_KEY", "test-secret")
    with _remote_server(fail_search_attempts=1) as (base_url, requests):
        backend = _backend(
            base_url,
            api_retry_count=1,
            api_retry_backoff_seconds=0.0,
        )
        result = backend.search(query="Nat", limit=1, rerank_top=0, packages=None)

    assert result.items[0].id == 7
    assert [request["path"] for request in requests].count("/api/v2/search") == 2


def test_api_backend_requires_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEANEXPLORE_TEST_KEY", raising=False)
    backend = _backend("http://127.0.0.1:1/api/v2")
    with pytest.raises(RuntimeError, match="missing API key environment variable"):
        backend.search(query="Nat", limit=1, rerank_top=0, packages=None)


def test_api_backend_startup_validation_always_requires_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LEANEXPLORE_TEST_KEY", raising=False)
    backend = _backend(
        "http://127.0.0.1:1/api/v2",
        api_verify_on_startup=False,
    )

    with pytest.raises(RuntimeError, match="missing API key environment variable"):
        backend.validate_startup()
