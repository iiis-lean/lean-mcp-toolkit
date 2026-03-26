"""LeanFinder provider adapter."""

from __future__ import annotations

import re

from ...config import LeanFinderProviderConfig
from .http_common import SearchHttpHelper


class LeanFinderProvider:
    def __init__(self, *, config: LeanFinderProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, query: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        data = self.http_helper.post_json(
            url=self.config.base_url,
            payload={"inputs": query, "top_k": int(num_results)},
            timeout_seconds=self.config.timeout_seconds,
        )
        results = data.get("results", []) if isinstance(data, dict) else []
        items: list[dict] = []
        if not isinstance(results, list):
            return items
        for result in results[:num_results]:
            if not isinstance(result, dict):
                continue
            url = str(result.get("url") or "")
            if self.config.mathlib_docs_only and "mathlib4_docs" not in url:
                continue
            match = re.search(r"pattern=(.*?)#doc", url)
            full_name = match.group(1) if match else ""
            items.append(
                {
                    "full_name": full_name,
                    "formal_statement": str(result.get("formal_statement") or ""),
                    "informal_statement": str(result.get("informal_statement") or ""),
                    "raw_payload": dict(result) if include_raw_payload else None,
                }
            )
        return items

