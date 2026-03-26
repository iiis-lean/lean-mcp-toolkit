"""LeanDex provider adapter."""

from __future__ import annotations

from ...config import LeanDexProviderConfig
from .http_common import SearchHttpHelper, build_url


class LeanDexProvider:
    def __init__(self, *, config: LeanDexProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, query: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        url = build_url(
            self.config.base_url,
            "/api/v1/search",
            {
                "q": query,
                "limit": str(num_results),
                "generate_query": str(self.config.generate_query).lower(),
                "analyze_result": str(self.config.analyze_result).lower(),
            },
        )
        payload = self.http_helper.get_sse_json(
            url=url,
            timeout_seconds=self.config.timeout_seconds,
        )
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        raw_results = data.get("search_results", []) if isinstance(data, dict) else []
        items: list[dict] = []
        if not isinstance(raw_results, list):
            return items
        for result in raw_results[:num_results]:
            if not isinstance(result, dict):
                continue
            primary = result.get("primary_declaration")
            if isinstance(primary, dict):
                primary_name = str(primary.get("lean_name") or "")
            else:
                primary_name = str(primary or "")
            items.append(
                {
                    "primary_declaration": primary_name,
                    "source_file": result.get("source_file"),
                    "start_line": result.get("range_start_line"),
                    "end_line": result.get("range_end_line"),
                    "statement": result.get("display_statement_text"),
                    "full_statement": result.get("statement_text"),
                    "docstring": result.get("docstring"),
                    "informal_description": result.get("informal_description"),
                    "raw_payload": dict(result) if include_raw_payload else None,
                }
            )
        return items

