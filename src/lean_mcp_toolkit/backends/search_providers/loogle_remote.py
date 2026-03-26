"""Remote Loogle adapter."""

from __future__ import annotations

from ...config import LoogleProviderConfig
from .http_common import SearchHttpHelper, build_url


class LoogleRemoteProvider:
    def __init__(self, *, config: LoogleProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, query: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        url = build_url(self.config.remote_base_url, "/json", {"q": query})
        data = self.http_helper.get_json(
            url=url,
            timeout_seconds=self.config.remote_timeout_seconds,
        )
        hits = data.get("hits", []) if isinstance(data, dict) else []
        items: list[dict] = []
        if not isinstance(hits, list):
            return items
        for hit in hits[:num_results]:
            if not isinstance(hit, dict):
                continue
            items.append(
                {
                    "name": str(hit.get("name") or ""),
                    "type": str(hit.get("type") or ""),
                    "module": str(hit.get("module") or ""),
                    "raw_payload": dict(hit) if include_raw_payload else None,
                }
            )
        return items

