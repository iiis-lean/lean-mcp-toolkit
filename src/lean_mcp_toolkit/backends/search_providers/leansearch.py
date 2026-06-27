"""LeanSearch provider adapter."""

from __future__ import annotations

from ...config import LeanSearchProviderConfig
from .http_common import SearchHttpHelper, build_url

THEOREM_SEARCH_TASK = (
    "Given a math statement, retrieve useful references, such as theorems, "
    "lemmas, and definitions, that are useful for solving the given problem."
)


class LeanSearchProvider:
    def __init__(self, *, config: LeanSearchProviderConfig, http_helper: SearchHttpHelper):
        self.config = config
        self.http_helper = http_helper

    def search(self, *, query: str, num_results: int, include_raw_payload: bool) -> list[dict]:
        url = build_url(self.config.base_url, "/search")
        payload = {"num_results": str(num_results), "query": [query]}
        data = self.http_helper.post_json(
            url=url,
            payload=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        if not isinstance(data, list) or not data or not isinstance(data[0], list):
            return []
        items: list[dict] = []
        for entry in data[0][:num_results]:
            if not isinstance(entry, dict):
                continue
            raw = entry.get("result")
            if not isinstance(raw, dict):
                continue
            items.append(
                {
                    "name": ".".join(str(part) for part in (raw.get("name") or [])),
                    "module_name": ".".join(str(part) for part in (raw.get("module_name") or [])),
                    "kind": raw.get("kind"),
                    "type": raw.get("type"),
                    "formal_statement": raw.get("signature") or raw.get("formal_statement"),
                    "informal_name": raw.get("informal_name"),
                    "informal_description": raw.get("informal_description"),
                    "raw_payload": dict(raw) if include_raw_payload else None,
                }
            )
        return items

    def search_arxiv_theorems(
        self,
        *,
        query: str,
        num_results: int,
        include_raw_payload: bool,
    ) -> list[dict]:
        url = build_url(self.config.base_url, "/thm/search")
        payload = {
            "query": query,
            "task": THEOREM_SEARCH_TASK,
            "num_results": num_results,
        }
        data = self.http_helper.post_json(
            url=url,
            payload=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        if not isinstance(data, list):
            return []
        items: list[dict] = []
        for entry in data[:num_results]:
            if not isinstance(entry, dict):
                continue
            items.append(
                {
                    "title": str(entry.get("title") or ""),
                    "theorem": str(entry.get("theorem") or ""),
                    "arxiv_id": str(entry.get("arxiv_id") or ""),
                    "theorem_id": str(entry.get("theorem_id") or ""),
                    "raw_payload": dict(entry) if include_raw_payload else None,
                }
            )
        return items
