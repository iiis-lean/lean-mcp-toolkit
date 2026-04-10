"""HTTP client configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ...contracts.base import JsonDict, to_bool, to_int


@dataclass(slots=True, frozen=True)
class HttpConfig:
    base_url: str
    api_prefix: str = "/api/v1"
    tool_view: str | None = None
    timeout_seconds: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    auth_token: str | None = None
    retry_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "HttpConfig":
        timeout_raw = data.get("timeout_seconds")
        timeout = 30.0
        if timeout_raw is not None:
            try:
                timeout = float(timeout_raw)
            except (TypeError, ValueError):
                timeout = 30.0

        raw_headers = data.get("headers")
        headers: dict[str, str] = {}
        if isinstance(raw_headers, dict):
            headers = {str(k): str(v) for k, v in raw_headers.items()}

        return cls(
            base_url=str(data.get("base_url") or "").rstrip("/"),
            api_prefix=str(data.get("api_prefix") or "/api/v1"),
            tool_view=(str(data["tool_view"]).strip() if data.get("tool_view") is not None else None),
            timeout_seconds=timeout,
            headers=headers,
            verify_ssl=to_bool(data.get("verify_ssl"), default=True),
            auth_token=(str(data["auth_token"]) if data.get("auth_token") is not None else None),
            retry_count=to_int(data.get("retry_count"), default=0) or 0,
        )

    def to_dict(self) -> JsonDict:
        return {
            "base_url": self.base_url,
            "api_prefix": self.api_prefix,
            "tool_view": self.tool_view,
            "timeout_seconds": self.timeout_seconds,
            "headers": dict(self.headers),
            "verify_ssl": self.verify_ssl,
            "auth_token": self.auth_token,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        prefix: str = "LEAN_MCP_TOOLKIT_HTTP__",
    ) -> "HttpConfig":
        get = lambda key: env.get(prefix + key)
        headers_raw = get("HEADERS")
        headers: dict[str, str] = {}
        if headers_raw:
            # format: k1:v1,k2:v2
            for part in headers_raw.split(","):
                item = part.strip()
                if not item or ":" not in item:
                    continue
                k, v = item.split(":", 1)
                headers[k.strip()] = v.strip()

        return cls(
            base_url=(get("BASE_URL") or "").rstrip("/"),
            api_prefix=get("API_PREFIX") or "/api/v1",
            tool_view=get("TOOL_VIEW"),
            timeout_seconds=float(get("TIMEOUT_SECONDS") or "30"),
            headers=headers,
            verify_ssl=to_bool(get("VERIFY_SSL"), default=True),
            auth_token=get("AUTH_TOKEN"),
            retry_count=int(get("RETRY_COUNT") or "0"),
        )
