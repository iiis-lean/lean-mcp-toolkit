"""Hammer-premise provider adapter."""

from __future__ import annotations

from ...config import HammerPremiseProviderConfig
from .http_common import SearchHttpHelper, build_url


class HammerPremiseProvider:
    def __init__(self, *, config: HammerPremiseProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, goal: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        url = build_url(self.config.base_url, "/retrieve")
        data = self.http_helper.post_json(
            url=url,
            payload={"state": goal, "new_premises": [], "k": num_results},
            timeout_seconds=self.config.timeout_seconds,
        )
        if not isinstance(data, list):
            return []
        items: list[dict] = []
        for result in data[:num_results]:
            if not isinstance(result, dict):
                continue
            items.append(
                {
                    "name": str(result.get("name") or ""),
                    "raw_payload": dict(result) if include_raw_payload else None,
                }
            )
        return items

