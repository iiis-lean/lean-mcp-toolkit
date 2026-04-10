import socket

import pytest

from lean_mcp_toolkit.transport.http.base_client import HttpJsonClient
from lean_mcp_toolkit.transport.http.config import HttpConfig
from lean_mcp_toolkit.transport.http.errors import HttpClientError


def test_http_client_error_message_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args, **kwargs):
        _ = args
        _ = kwargs
        raise socket.timeout("timed out")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    client = HttpJsonClient(HttpConfig(base_url="http://127.0.0.1:9999", retry_count=0))

    with pytest.raises(HttpClientError, match="http request failed: timed out"):
        client.post_json("/diagnostics/lint", {"targets": ["A/Pkg.lean"]})


def test_http_client_error_message_with_retry_count(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args, **kwargs):
        _ = args
        _ = kwargs
        raise socket.timeout("timed out")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    client = HttpJsonClient(HttpConfig(base_url="http://127.0.0.1:9999", retry_count=2))

    with pytest.raises(HttpClientError, match="http request failed after 3 attempts: timed out"):
        client.post_json("/diagnostics/lint", {"targets": ["A/Pkg.lean"]})


def test_http_client_builds_tool_view_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_urls: list[str] = []

    def _raise(request, *args, **kwargs):
        _ = args
        _ = kwargs
        seen_urls.append(request.full_url)
        raise socket.timeout("timed out")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    client = HttpJsonClient(
        HttpConfig(
            base_url="http://127.0.0.1:9999",
            api_prefix="/api/v1",
            tool_view="proof",
            retry_count=0,
        )
    )

    with pytest.raises(HttpClientError):
        client.get_json("/meta/tools")

    assert seen_urls == ["http://127.0.0.1:9999/api/v1/views/proof/meta/tools"]
