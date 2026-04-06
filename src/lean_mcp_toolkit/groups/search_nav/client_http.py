"""HTTP-backed search_nav client."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_nav import (
    LocalDeclFindRequest,
    LocalDeclFindResponse,
    LocalImportFindRequest,
    LocalImportFindResponse,
    LocalRefsFindRequest,
    LocalRefsFindResponse,
    LocalScopeFindRequest,
    LocalScopeFindResponse,
    LocalTextFindRequest,
    LocalTextFindResponse,
    RepoNavFileOutlineRequest,
    RepoNavFileOutlineResponse,
    RepoNavGrepRequest,
    RepoNavGrepResponse,
    RepoNavReadRequest,
    RepoNavReadResponse,
    RepoNavTreeRequest,
    RepoNavTreeResponse,
)
from ...core.services import SearchNavService
from ...transport.http import HttpConfig, HttpJsonClient


class SearchNavHttpClient(SearchNavService):
    def __init__(self, http_config: HttpConfig, *, http_client: HttpJsonClient | None = None):
        self.http_config = http_config
        self.http_client = http_client or HttpJsonClient(http_config)

    def run_repo_nav_tree(self, req: RepoNavTreeRequest) -> RepoNavTreeResponse:
        return RepoNavTreeResponse.from_dict(self._post("/search/repo_nav/tree", req.to_dict()))

    def run_repo_nav_file_outline(
        self,
        req: RepoNavFileOutlineRequest,
    ) -> RepoNavFileOutlineResponse:
        return RepoNavFileOutlineResponse.from_dict(
            self._post("/search/repo_nav/file_outline", req.to_dict())
        )

    def run_repo_nav_grep(self, req: RepoNavGrepRequest) -> RepoNavGrepResponse:
        return RepoNavGrepResponse.from_dict(self._post("/search/repo_nav/grep", req.to_dict()))

    def run_repo_nav_read(self, req: RepoNavReadRequest) -> RepoNavReadResponse:
        return RepoNavReadResponse.from_dict(self._post("/search/repo_nav/read", req.to_dict()))

    def run_local_decl_find(self, req: LocalDeclFindRequest) -> LocalDeclFindResponse:
        return LocalDeclFindResponse.from_dict(self._post("/search/local_decl/find", req.to_dict()))

    def run_local_import_find(self, req: LocalImportFindRequest) -> LocalImportFindResponse:
        return LocalImportFindResponse.from_dict(
            self._post("/search/local_import/find", req.to_dict())
        )

    def run_local_scope_find(self, req: LocalScopeFindRequest) -> LocalScopeFindResponse:
        return LocalScopeFindResponse.from_dict(self._post("/search/local_scope/find", req.to_dict()))

    def run_local_text_find(self, req: LocalTextFindRequest) -> LocalTextFindResponse:
        return LocalTextFindResponse.from_dict(self._post("/search/local_text/find", req.to_dict()))

    def run_local_refs_find(self, req: LocalRefsFindRequest) -> LocalRefsFindResponse:
        return LocalRefsFindResponse.from_dict(self._post("/search/local_refs/find", req.to_dict()))

    def _post(self, path: str, payload: JsonDict) -> JsonDict:
        return self.http_client.post_json(path, payload)


__all__ = ["SearchNavHttpClient"]
