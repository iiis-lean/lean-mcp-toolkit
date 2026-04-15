"""HTTP-adapter handlers for search_nav tools."""

from __future__ import annotations

from ...contracts.base import JsonDict
from ...contracts.search_nav import (
    LocalDeclFindRequest,
    LocalImportFindRequest,
    LocalRefsFindRequest,
    LocalScopeFindRequest,
    LocalTextFindRequest,
    RepoNavFileOutlineRequest,
    RepoNavGrepRequest,
    RepoNavReadRequest,
    RepoNavTreeRequest,
)
from ...core.services import SearchNavService


def handle_search_repo_nav_tree(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = RepoNavTreeRequest.from_dict(payload)
    return service.run_repo_nav_tree(req)


def handle_search_repo_nav_file_outline(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = RepoNavFileOutlineRequest.from_dict(payload)
    return service.run_repo_nav_file_outline(req)


def handle_search_repo_nav_grep(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = RepoNavGrepRequest.from_dict(payload)
    return service.run_repo_nav_grep(req)


def handle_search_repo_nav_read(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = RepoNavReadRequest.from_dict(payload)
    return service.run_repo_nav_read(req)


def handle_search_local_decl_find(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = LocalDeclFindRequest.from_dict(payload)
    return service.run_local_decl_find(req)


def handle_search_local_import_find(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = LocalImportFindRequest.from_dict(payload)
    return service.run_local_import_find(req)


def handle_search_local_scope_find(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = LocalScopeFindRequest.from_dict(payload)
    return service.run_local_scope_find(req)


def handle_search_local_text_find(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = LocalTextFindRequest.from_dict(payload)
    return service.run_local_text_find(req)


def handle_search_local_refs_find(service: SearchNavService, payload: JsonDict) -> JsonDict:
    req = LocalRefsFindRequest.from_dict(payload)
    return service.run_local_refs_find(req)


__all__ = [
    "handle_search_repo_nav_tree",
    "handle_search_repo_nav_file_outline",
    "handle_search_repo_nav_grep",
    "handle_search_repo_nav_read",
    "handle_search_local_decl_find",
    "handle_search_local_import_find",
    "handle_search_local_scope_find",
    "handle_search_local_text_find",
    "handle_search_local_refs_find",
]
