"""Search-alt backend manager."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...config import SearchProvidersConfig
from .http_common import SearchHttpHelper
from .leandex import LeanDexProvider
from .leanfinder import LeanFinderProvider
from .leansearch import LeanSearchProvider
from .loogle_local import LoogleLocalManager
from .loogle_remote import LoogleRemoteProvider


@dataclass(slots=True)
class SearchAltBackendManager:
    config: SearchProvidersConfig
    http_helper: SearchHttpHelper
    leansearch: LeanSearchProvider
    leandex: LeanDexProvider
    loogle_remote: LoogleRemoteProvider
    loogle_local: LoogleLocalManager
    leanfinder: LeanFinderProvider

    def __init__(self, *, config: SearchProvidersConfig):
        self.config = config
        self.http_helper = SearchHttpHelper(config=config.http_common)
        self.leansearch = LeanSearchProvider(config=config.leansearch, http_helper=self.http_helper)
        self.leandex = LeanDexProvider(config=config.leandex, http_helper=self.http_helper)
        self.loogle_remote = LoogleRemoteProvider(config=config.loogle, http_helper=self.http_helper)
        self.loogle_local = LoogleLocalManager(config=config.loogle)
        self.leanfinder = LeanFinderProvider(config=config.leanfinder, http_helper=self.http_helper)

    def search_loogle(
        self,
        *,
        query: str,
        num_results: int,
        include_raw_payload: bool,
        project_root: Path | None,
    ) -> tuple[str, list[dict]]:
        mode = self.config.loogle.mode
        if mode in {"local", "prefer_local"}:
            try:
                local_items = self.loogle_local.query(
                    query=query,
                    num_results=num_results,
                    project_root=project_root,
                )
                return ("local", self._maybe_strip_raw(local_items, include_raw_payload))
            except Exception:
                if mode == "local" or not self.config.loogle.local_fallback_to_remote:
                    raise
        remote_items = self.loogle_remote.search(
            query=query,
            num_results=num_results,
            include_raw_payload=include_raw_payload,
        )
        return ("remote", remote_items)

    @staticmethod
    def _maybe_strip_raw(items: list[dict], include_raw_payload: bool) -> list[dict]:
        if include_raw_payload:
            return items
        out: list[dict] = []
        for item in items:
            copied = dict(item)
            copied["raw_payload"] = None
            out.append(copied)
        return out

