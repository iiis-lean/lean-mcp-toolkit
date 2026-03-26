"""State-search provider adapter."""

from __future__ import annotations

from ...config import StateSearchProviderConfig
from .http_common import SearchHttpHelper, build_url


class StateSearchProvider:
    def __init__(self, *, config: StateSearchProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, goal: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        url = build_url(
            self.config.base_url,
            "/api/search",
            {
                "query": goal,
                "results": str(num_results),
                "rev": self.config.revision,
            },
        )
        data = self.http_helper.get_json(url=url, timeout_seconds=self.config.timeout_seconds)
        if not isinstance(data, list):
            return []
        items: list[dict] = []
        for result in data[:num_results]:
            if not isinstance(result, dict):
                continue
            items.append(
                {
                    "name": str(result.get("name") or ""),
                    "formal_type": (
                        str(result["formal_type"]) if result.get("formal_type") is not None else None
                    ),
                    "module": str(result["module"]) if result.get("module") is not None else None,
                    "raw_payload": dict(result) if include_raw_payload else None,
                }
            )
        return items

