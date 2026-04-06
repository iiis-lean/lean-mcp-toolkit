"""search_nav service implementation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Iterable

from ...config import ToolkitConfig
from ...contracts.search_nav import (
    LocalDeclFindItem,
    LocalDeclFindRequest,
    LocalDeclFindResponse,
    LocalImportEdgeItem,
    LocalImportFindRequest,
    LocalImportFindResponse,
    LocalRefsFindItem,
    LocalRefsFindRequest,
    LocalRefsFindResponse,
    LocalScopeFindItem,
    LocalScopeFindRequest,
    LocalScopeFindResponse,
    LocalTextFindItem,
    LocalTextFindRequest,
    LocalTextFindResponse,
    RepoNavDeclarationItem,
    RepoNavFileOutlineRequest,
    RepoNavFileOutlineResponse,
    RepoNavGrepRequest,
    RepoNavGrepResponse,
    RepoNavOutlineSummary,
    RepoNavReadRequest,
    RepoNavReadResponse,
    RepoNavReadWindow,
    RepoNavResolution,
    RepoNavScopeCmdItem,
    RepoNavSectionItem,
    RepoNavTarget,
    RepoNavTreeEntry,
    RepoNavTreePage,
    RepoNavTreeRequest,
    RepoNavTreeResponse,
)
from ...core.services import SearchNavService

_DECL_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:private|protected|noncomputable|unsafe|partial|nonrec)\s+)*)"
    r"(?P<kind>theorem|lemma|def|axiom|abbrev|opaque|inductive|structure|class|instance)\b(?P<rest>.*)$"
)
_NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_'.]+)")
_END_RE = re.compile(r"^\s*end(?:\s+([A-Za-z0-9_'.]+))?\s*$")
_IMPORT_RE = re.compile(r"^\s*(?:(public|meta)\s+)?import\s+(.+)$")
_SECTION_RE = re.compile(r"^\s*section(?:\s+([A-Za-z0-9_'.]+))?\s*$")
_OPEN_SCOPED_RE = re.compile(r"^\s*open\s+scoped\s+(.+)$")
_OPEN_RE = re.compile(r"^\s*open\s+(.+)$")
_EXPORT_RE = re.compile(r"^\s*export\s+(.+)$")
_ATTRIBUTE_RE = re.compile(r"^\s*attribute\s+(.+)$")

_SCOPE_KINDS_DEFAULT = (
    "namespace",
    "section",
    "open",
    "open_scoped",
    "export",
    "attribute",
)

_TEXT_SCOPES_DEFAULT = (
    "module_doc",
    "section_doc",
    "decl_doc",
    "decl_header",
    "decl_sig",
)

_GREP_SCOPES_DEFAULT = (
    "decl_header",
    "decl_sig",
    "body",
    "comment",
)

_REF_SCOPES_DEFAULT = (
    "decl_header",
    "import",
    "scope_cmd",
    "body",
)


@dataclass(slots=True, frozen=True)
class _LeanFile:
    abs_path: Path
    file_path: str
    module_path: str | None
    origin: str


@dataclass(slots=True, frozen=True)
class _DeclarationRecord:
    full_name: str
    short_name: str
    decl_kind: str
    file_path: str
    module_path: str | None
    line_start: int
    line_end: int | None
    header_preview: str
    visibility: str | None


@dataclass(slots=True, frozen=True)
class _ScopeRecord:
    scope_kind: str
    target: str | None
    file_path: str
    module_path: str | None
    line_start: int
    line_end: int | None


@dataclass(slots=True, frozen=True)
class _DocBlock:
    kind: str
    text: str
    line_start: int
    line_end: int


@dataclass(slots=True)
class SearchNavServiceImpl(SearchNavService):
    config: ToolkitConfig

    def run_repo_nav_tree(self, req: RepoNavTreeRequest) -> RepoNavTreeResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            depth = req.depth if req.depth is not None else 1
            depth = max(0, depth)
            limit = req.limit if req.limit is not None else self.config.search_nav.default_limit
            offset = max(0, req.offset or 0)

            base_abs, base_rel, base_module = self._resolve_tree_base(repo_root, req.base)

            all_entries: list[RepoNavTreeEntry] = []
            self._collect_tree_entries(
                repo_root=repo_root,
                current=base_abs,
                depth=depth,
                name_filter=(req.name_filter or "").strip(),
                out=all_entries,
            )

            page_entries = all_entries[offset : offset + limit]
            next_offset = offset + limit if offset + limit < len(all_entries) else None

            return RepoNavTreeResponse(
                success=True,
                error_message=None,
                resolution=RepoNavResolution(
                    repo_root=str(repo_root),
                    source_root=str(repo_root),
                    base_path=base_rel,
                    base_module=base_module,
                ),
                entries=tuple(page_entries),
                page=RepoNavTreePage(
                    offset=offset,
                    limit=limit,
                    returned=len(page_entries),
                    next_offset=next_offset,
                ),
            )
        except Exception as exc:
            return RepoNavTreeResponse(success=False, error_message=str(exc))

    def run_repo_nav_file_outline(
        self,
        req: RepoNavFileOutlineRequest,
    ) -> RepoNavFileOutlineResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            abs_path, file_path, module_path = self._resolve_target_file(repo_root, req.target)
            lines = self._read_lines(abs_path)

            include_imports = (
                req.include_imports
                if req.include_imports is not None
                else self.config.search_nav.outline_include_imports_default
            )
            include_module_doc = (
                req.include_module_doc
                if req.include_module_doc is not None
                else self.config.search_nav.outline_include_module_doc_default
            )
            include_section_doc = (
                req.include_section_doc
                if req.include_section_doc is not None
                else self.config.search_nav.outline_include_section_doc_default
            )
            include_decl_headers = (
                req.include_decl_headers
                if req.include_decl_headers is not None
                else self.config.search_nav.outline_include_decl_headers_default
            )
            include_scope_cmds = (
                req.include_scope_cmds
                if req.include_scope_cmds is not None
                else self.config.search_nav.outline_include_scope_cmds_default
            )
            limit_decls = req.limit_decls or self.config.search_nav.outline_default_limit_decls

            imports = tuple(self._extract_import_modules(lines)) if include_imports else tuple()
            docs = self._extract_doc_blocks(lines)
            module_doc = None
            sections: list[RepoNavSectionItem] = []
            if include_module_doc or include_section_doc:
                bang_docs = [block for block in docs if block.kind == "bang_doc"]
                if include_module_doc and bang_docs:
                    module_doc = bang_docs[0].text
                if include_section_doc:
                    for block in bang_docs[1:]:
                        title_line = block.text.splitlines()[0].strip() if block.text.strip() else ""
                        sections.append(
                            RepoNavSectionItem(
                                title=title_line,
                                line_start=block.line_start,
                                line_end=block.line_end,
                            )
                        )

            declarations: list[RepoNavDeclarationItem] = []
            if include_decl_headers:
                decl_records = self._extract_declarations(
                    lines=lines,
                    file_path=file_path,
                    module_path=module_path,
                )
                for rec in decl_records[:limit_decls]:
                    declarations.append(
                        RepoNavDeclarationItem(
                            decl_kind=rec.decl_kind,
                            full_name=rec.full_name,
                            line_start=rec.line_start,
                            line_end=rec.line_end,
                            header_preview=rec.header_preview,
                        )
                    )

            scope_cmds: list[RepoNavScopeCmdItem] = []
            if include_scope_cmds:
                for rec in self._extract_scope_cmds(lines=lines, file_path=file_path, module_path=module_path):
                    scope_cmds.append(
                        RepoNavScopeCmdItem(
                            kind=rec.scope_kind,
                            target=rec.target,
                            line_start=rec.line_start,
                            line_end=rec.line_end,
                        )
                    )

            return RepoNavFileOutlineResponse(
                success=True,
                error_message=None,
                target=RepoNavTarget(file_path=file_path, module_path=module_path),
                imports=imports,
                module_doc=module_doc,
                sections=tuple(sections),
                declarations=tuple(declarations),
                scope_cmds=tuple(scope_cmds),
                summary=RepoNavOutlineSummary(
                    total_lines=len(lines),
                    decl_count=len(declarations),
                ),
            )
        except Exception as exc:
            return RepoNavFileOutlineResponse(success=False, error_message=str(exc))

    def run_repo_nav_read(self, req: RepoNavReadRequest) -> RepoNavReadResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            abs_path, file_path, module_path = self._resolve_target_file(repo_root, req.target)
            lines = self._read_lines(abs_path)

            total = len(lines)
            start_line = max(1, req.start_line or 1)
            max_lines = req.max_lines or self.config.search_nav.read_default_max_lines
            end_line = req.end_line if req.end_line is not None else (start_line + max_lines - 1)
            if end_line < start_line:
                end_line = start_line
            if end_line - start_line + 1 > max_lines:
                end_line = start_line + max_lines - 1
            end_line = min(end_line, total)

            start_idx = max(0, start_line - 1)
            end_idx = max(start_idx, end_line - 1)
            slice_lines = lines[start_idx : end_idx + 1]

            with_line_numbers = (
                req.with_line_numbers
                if req.with_line_numbers is not None
                else self.config.search_nav.read_with_line_numbers_default
            )
            if with_line_numbers:
                content = "\n".join(
                    f"{start_idx + idx + 1:>5} | {line}" for idx, line in enumerate(slice_lines)
                )
            else:
                content = "\n".join(slice_lines)

            truncated = end_line < total
            next_start_line = end_line + 1 if truncated else None

            return RepoNavReadResponse(
                success=True,
                error_message=None,
                target=RepoNavTarget(file_path=file_path, module_path=module_path),
                window=RepoNavReadWindow(
                    start_line=start_line,
                    end_line=end_line,
                    total_lines=total,
                    truncated=truncated,
                    next_start_line=next_start_line,
                ),
                content=content,
            )
        except Exception as exc:
            return RepoNavReadResponse(success=False, error_message=str(exc))

    def run_repo_nav_grep(self, req: RepoNavGrepRequest) -> RepoNavGrepResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = req.include_deps if req.include_deps is not None else True
            limit = req.limit or self.config.search_nav.default_limit
            context_lines = req.context_lines if req.context_lines is not None else 1
            query = req.query.strip()
            path_filter = self._normalize_path_filter(repo_root, req.path_filter)
            module_filter = (req.module_filter or "").strip()
            scopes = tuple(req.scopes or _GREP_SCOPES_DEFAULT)

            if not query:
                return RepoNavGrepResponse(
                    success=True,
                    query="",
                    match_mode=req.match_mode,
                    path_filter=path_filter,
                    count=0,
                    items=tuple(),
                )

            items: list[LocalTextFindItem] = []
            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if path_filter and not self._matches_path_filter(lean_file.file_path, path_filter):
                    continue
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue
                lines = self._read_lines(lean_file.abs_path)
                for item in self._extract_text_hits(
                    lines=lines,
                    file_path=lean_file.file_path,
                    module_path=lean_file.module_path,
                    query=query,
                    text_match=req.match_mode,
                    scopes=scopes,
                    context_lines=context_lines,
                ):
                    items.append(item)
                    if len(items) >= limit:
                        return RepoNavGrepResponse(
                            success=True,
                            query=query,
                            match_mode=req.match_mode,
                            path_filter=path_filter,
                            count=len(items),
                            items=tuple(items),
                        )

            return RepoNavGrepResponse(
                success=True,
                query=query,
                match_mode=req.match_mode,
                path_filter=path_filter,
                count=len(items),
                items=tuple(items),
            )
        except Exception as exc:
            return RepoNavGrepResponse(
                success=False,
                error_message=str(exc),
                query=req.query,
                match_mode=req.match_mode,
                path_filter=req.path_filter,
            )

    def run_local_decl_find(self, req: LocalDeclFindRequest) -> LocalDeclFindResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = (
                req.include_deps
                if req.include_deps is not None
                else self.config.search_nav.include_deps_default
            )
            limit = req.limit or self.config.search_nav.default_limit
            query = req.query.strip()
            if not query:
                return LocalDeclFindResponse(success=True, query="", count=0, items=tuple())

            allowed_kinds = set(k.strip() for k in (req.decl_kinds or ()) if k.strip())
            namespace_filter = (req.namespace_filter or "").strip()
            module_filter = (req.module_filter or "").strip()

            items: list[LocalDeclFindItem] = []
            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue
                lines = self._read_lines(lean_file.abs_path)
                declarations = self._extract_declarations(
                    lines=lines,
                    file_path=lean_file.file_path,
                    module_path=lean_file.module_path,
                )
                for rec in declarations:
                    if allowed_kinds and rec.decl_kind not in allowed_kinds:
                        continue
                    if namespace_filter and not (
                        rec.full_name == namespace_filter
                        or rec.full_name.startswith(namespace_filter + ".")
                    ):
                        continue
                    if not self._match_text(rec.full_name, query, req.match_mode):
                        continue
                    items.append(
                        LocalDeclFindItem(
                            full_name=rec.full_name,
                            short_name=rec.short_name,
                            decl_kind=rec.decl_kind,
                            module_path=rec.module_path,
                            file_path=rec.file_path,
                            line_start=rec.line_start,
                            line_end=rec.line_end,
                            header_preview=rec.header_preview,
                            visibility=rec.visibility,
                        )
                    )
                    if len(items) >= limit:
                        return LocalDeclFindResponse(
                            success=True,
                            query=query,
                            count=len(items),
                            items=tuple(items),
                        )

            return LocalDeclFindResponse(
                success=True,
                query=query,
                count=len(items),
                items=tuple(items),
            )
        except Exception as exc:
            return LocalDeclFindResponse(success=False, error_message=str(exc), query=req.query)

    def run_local_import_find(self, req: LocalImportFindRequest) -> LocalImportFindResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = (
                req.include_deps
                if req.include_deps is not None
                else self.config.search_nav.include_deps_default
            )
            limit = req.limit or self.config.search_nav.default_limit
            query = req.query.strip()
            if not query:
                return LocalImportFindResponse(success=True, query="", count=0, edges=tuple())

            module_filter = (req.module_filter or "").strip()
            edges: list[LocalImportEdgeItem] = []

            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue
                lines = self._read_lines(lean_file.abs_path)
                imports = self._extract_import_edges(lines)
                for imported_module, line_no in imports:
                    importer_module = lean_file.module_path
                    match = False
                    if req.direction == "imports":
                        match = self._match_text(importer_module or "", query, req.match_mode)
                    else:
                        match = self._match_text(imported_module, query, req.match_mode)
                    if not match:
                        continue
                    edges.append(
                        LocalImportEdgeItem(
                            importer_module=importer_module,
                            importer_file=lean_file.file_path,
                            imported_module=imported_module,
                            line_start=line_no,
                            line_end=line_no,
                        )
                    )
                    if len(edges) >= limit:
                        return LocalImportFindResponse(
                            success=True,
                            query=query,
                            count=len(edges),
                            edges=tuple(edges),
                        )

            return LocalImportFindResponse(
                success=True,
                query=query,
                count=len(edges),
                edges=tuple(edges),
            )
        except Exception as exc:
            return LocalImportFindResponse(success=False, error_message=str(exc), query=req.query)

    def run_local_scope_find(self, req: LocalScopeFindRequest) -> LocalScopeFindResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = (
                req.include_deps
                if req.include_deps is not None
                else self.config.search_nav.include_deps_default
            )
            limit = req.limit or self.config.search_nav.default_limit
            context_lines = (
                req.context_lines
                if req.context_lines is not None
                else self.config.search_nav.default_context_lines
            )
            query = (req.query or "").strip()
            kinds = set(req.scope_kinds or _SCOPE_KINDS_DEFAULT)
            module_filter = (req.module_filter or "").strip()

            items: list[LocalScopeFindItem] = []
            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue
                lines = self._read_lines(lean_file.abs_path)
                for rec in self._extract_scope_cmds(
                    lines=lines,
                    file_path=lean_file.file_path,
                    module_path=lean_file.module_path,
                ):
                    if rec.scope_kind not in kinds:
                        continue
                    if query and not self._match_text(rec.target or "", query, req.match_mode):
                        continue
                    items.append(
                        LocalScopeFindItem(
                            scope_kind=rec.scope_kind,
                            target=rec.target,
                            file_path=rec.file_path,
                            module_path=rec.module_path,
                            line_start=rec.line_start,
                            line_end=rec.line_end,
                            snippet=self._make_context_snippet(
                                lines=lines,
                                line_start=rec.line_start,
                                line_end=rec.line_end or rec.line_start,
                                context_lines=context_lines,
                            ),
                        )
                    )
                    if len(items) >= limit:
                        return LocalScopeFindResponse(success=True, count=len(items), items=tuple(items))

            return LocalScopeFindResponse(success=True, count=len(items), items=tuple(items))
        except Exception as exc:
            return LocalScopeFindResponse(success=False, error_message=str(exc), count=0, items=tuple())

    def run_local_text_find(self, req: LocalTextFindRequest) -> LocalTextFindResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = (
                req.include_deps
                if req.include_deps is not None
                else self.config.search_nav.include_deps_default
            )
            limit = req.limit or self.config.search_nav.default_limit
            context_lines = (
                req.context_lines
                if req.context_lines is not None
                else self.config.search_nav.default_context_lines
            )
            query = req.query.strip()
            if not query:
                return LocalTextFindResponse(success=True, query="", count=0, items=tuple())

            scopes = tuple(req.scopes or _TEXT_SCOPES_DEFAULT)
            module_filter = (req.module_filter or "").strip()

            items: list[LocalTextFindItem] = []
            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue
                lines = self._read_lines(lean_file.abs_path)
                for item in self._extract_text_hits(
                    lines=lines,
                    file_path=lean_file.file_path,
                    module_path=lean_file.module_path,
                    query=query,
                    text_match=req.text_match,
                    scopes=scopes,
                    context_lines=context_lines,
                ):
                    items.append(item)
                    if len(items) >= limit:
                        return LocalTextFindResponse(
                            success=True,
                            query=query,
                            count=len(items),
                            items=tuple(items),
                        )

            return LocalTextFindResponse(
                success=True,
                query=query,
                count=len(items),
                items=tuple(items),
            )
        except Exception as exc:
            return LocalTextFindResponse(success=False, error_message=str(exc), query=req.query)

    def run_local_refs_find(self, req: LocalRefsFindRequest) -> LocalRefsFindResponse:
        try:
            repo_root = self._resolve_repo_root(req.repo_root)
            include_deps = (
                req.include_deps
                if req.include_deps is not None
                else self.config.search_nav.include_deps_default
            )
            limit = req.limit or self.config.search_nav.default_limit
            context_lines = (
                req.context_lines
                if req.context_lines is not None
                else self.config.search_nav.default_context_lines
            )
            include_definition_site = (
                req.include_definition_site
                if req.include_definition_site is not None
                else self.config.search_nav.refs_include_definition_default
            )
            symbol = req.symbol.strip()
            if not symbol:
                return LocalRefsFindResponse(success=True, symbol="", count=0, items=tuple())

            scopes = set(req.scopes or _REF_SCOPES_DEFAULT)
            module_filter = (req.module_filter or "").strip()
            tail_symbol = symbol.rsplit(".", 1)[-1]

            items: list[LocalRefsFindItem] = []
            for lean_file in self._iter_lean_files(repo_root, include_deps=include_deps):
                if module_filter and not self._match_text(
                    lean_file.module_path or "",
                    module_filter,
                    "prefix",
                ):
                    continue

                lines = self._read_lines(lean_file.abs_path)
                declarations = self._extract_declarations(
                    lines=lines,
                    file_path=lean_file.file_path,
                    module_path=lean_file.module_path,
                )
                def_lines = {rec.line_start: rec for rec in declarations}

                full_pat = self._build_symbol_pattern(symbol)
                tail_pat = self._build_symbol_pattern(tail_symbol)

                for idx, line in enumerate(lines, start=1):
                    scope = self._infer_line_scope(line)
                    if scope not in scopes:
                        continue

                    matched_as = None
                    match_obj = None
                    if "." in symbol:
                        match_obj = full_pat.search(line)
                        if match_obj:
                            matched_as = "full_name"
                    if match_obj is None:
                        match_obj = tail_pat.search(line)
                        if match_obj:
                            matched_as = "tail_name"
                    if match_obj is None or matched_as is None:
                        continue

                    rec = def_lines.get(idx)
                    is_definition_site = False
                    if rec is not None:
                        if rec.full_name == symbol or rec.short_name == tail_symbol:
                            is_definition_site = True
                        elif rec.full_name.endswith("." + tail_symbol):
                            is_definition_site = True

                    if is_definition_site and not include_definition_site:
                        continue

                    items.append(
                        LocalRefsFindItem(
                            file_path=lean_file.file_path,
                            module_path=lean_file.module_path,
                            line_start=idx,
                            column_start=match_obj.start() + 1,
                            scope=scope,
                            snippet=self._make_context_snippet(
                                lines=lines,
                                line_start=idx,
                                line_end=idx,
                                context_lines=context_lines,
                            ),
                            is_definition_site=is_definition_site,
                            matched_as=matched_as,
                        )
                    )
                    if len(items) >= limit:
                        return LocalRefsFindResponse(
                            success=True,
                            symbol=symbol,
                            count=len(items),
                            items=tuple(items),
                        )

            return LocalRefsFindResponse(
                success=True,
                symbol=symbol,
                count=len(items),
                items=tuple(items),
            )
        except Exception as exc:
            return LocalRefsFindResponse(success=False, error_message=str(exc), symbol=req.symbol)

    def _resolve_repo_root(self, repo_root: str | None) -> Path:
        raw = repo_root or self.config.server.default_project_root or os.getcwd()
        root = Path(raw).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"repo_root is not a directory: {root}")
        return root

    def _resolve_tree_base(self, repo_root: Path, base: str | None) -> tuple[Path, str, str | None]:
        if not base or not base.strip():
            return repo_root, ".", None

        raw = base.strip()
        candidate_paths: list[Path] = []

        if raw.startswith("/"):
            candidate_paths.append(Path(raw).expanduser().resolve())
        else:
            candidate_paths.append((repo_root / raw).resolve())
            if "." in raw and "/" not in raw and "\\" not in raw:
                dot_rel = raw.replace(".", "/")
                candidate_paths.append((repo_root / dot_rel).resolve())
                candidate_paths.append((repo_root / f"{dot_rel}.lean").resolve())

        for path in candidate_paths:
            if path.exists():
                try:
                    rel = path.relative_to(repo_root).as_posix()
                except ValueError as exc:
                    raise ValueError(f"base path outside repo_root: {path}") from exc
                base_module = self._module_from_file_rel(rel) if path.is_file() else None
                return path, rel, base_module

        raise FileNotFoundError(f"base path not found: {raw}")

    def _collect_tree_entries(
        self,
        *,
        repo_root: Path,
        current: Path,
        depth: int,
        name_filter: str,
        out: list[RepoNavTreeEntry],
    ) -> None:
        if depth < 0 or not current.is_dir():
            return

        children = sorted(
            current.iterdir(),
            key=lambda p: (p.is_file(), p.name.lower()),
        )
        for child in children:
            if child.name in {".git", "__pycache__"}:
                continue
            if child.name == ".lake" and child.is_dir():
                continue
            if child.is_file() and child.suffix != ".lean":
                continue

            if name_filter and name_filter.casefold() not in child.name.casefold():
                continue

            rel = child.relative_to(repo_root).as_posix()
            kind = "dir" if child.is_dir() else "file"
            has_children = False
            child_count = None
            module_path = None
            if child.is_dir():
                try:
                    child_items = [
                        p
                        for p in child.iterdir()
                        if p.name not in {".git", "__pycache__"}
                        and not (p.name == ".lake" and p.is_dir())
                        and (p.is_dir() or p.suffix == ".lean")
                    ]
                    child_count = len(child_items)
                    has_children = child_count > 0
                except Exception:
                    child_count = None
                    has_children = False
            else:
                module_path = self._module_from_file_rel(rel)

            out.append(
                RepoNavTreeEntry(
                    kind=kind,
                    name=child.name,
                    relative_path=rel,
                    module_path=module_path,
                    has_children=has_children,
                    child_count=child_count,
                )
            )

            if child.is_dir() and depth > 0:
                self._collect_tree_entries(
                    repo_root=repo_root,
                    current=child,
                    depth=depth - 1,
                    name_filter=name_filter,
                    out=out,
                )

    def _resolve_target_file(self, repo_root: Path, target: str) -> tuple[Path, str, str | None]:
        raw = target.strip()
        if not raw:
            raise ValueError("target is required")

        candidates: list[Path] = []
        maybe_abs = Path(raw).expanduser()
        if maybe_abs.is_absolute():
            candidates.append(maybe_abs.resolve())
        else:
            candidates.append((repo_root / raw).resolve())
            if "." in raw and "/" not in raw and "\\" not in raw:
                dot_rel = raw.replace(".", "/")
                candidates.append((repo_root / f"{dot_rel}.lean").resolve())
            elif not raw.endswith(".lean"):
                candidates.append((repo_root / f"{raw}.lean").resolve())

        for path in candidates:
            if path.exists() and path.is_file():
                try:
                    rel = path.relative_to(repo_root).as_posix()
                except Exception as exc:
                    raise ValueError(f"target resolves outside repo_root: {path}") from exc
                module = self._module_from_file_rel(rel)
                return path, rel, module

        raise FileNotFoundError(f"target file not found: {target}")

    @staticmethod
    def _read_lines(path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        if text.endswith("\n"):
            if not lines or lines[-1] != "":
                pass
        return lines

    @staticmethod
    def _module_from_file_rel(file_rel: str) -> str | None:
        if not file_rel.endswith(".lean"):
            return None
        return file_rel[:-5].replace("/", ".")

    def _iter_lean_files(self, repo_root: Path, *, include_deps: bool) -> Iterable[_LeanFile]:
        max_files = max(1, self.config.search_nav.scan_max_files)
        max_file_bytes = max(1, self.config.search_nav.scan_max_file_bytes)

        roots: list[tuple[Path, str]] = [(repo_root, "project")]
        if include_deps:
            deps_root = repo_root / ".lake" / "packages"
            if deps_root.exists() and deps_root.is_dir():
                for pkg in sorted(deps_root.iterdir(), key=lambda p: p.name.lower()):
                    if pkg.is_dir():
                        roots.append((pkg, "dependency"))

        produced = 0
        for root, origin in roots:
            for path in sorted(root.rglob("*.lean")):
                if path.name.startswith("."):
                    continue
                path_str = path.as_posix()
                rel_to_root = path.relative_to(root).as_posix()
                rel_to_repo = path.relative_to(repo_root).as_posix()
                if "/.git/" in path_str or path_str.endswith("/.git"):
                    continue
                if rel_to_root.startswith(".lake/build/"):
                    continue
                if origin == "project" and rel_to_repo.startswith(".lake/packages/"):
                    continue
                try:
                    if path.stat().st_size > max_file_bytes:
                        continue
                except Exception:
                    continue

                if origin == "project":
                    rel = rel_to_repo
                else:
                    rel = f".lake/packages/{root.name}/{rel_to_root}"

                module_path = self._module_from_file_rel(rel_to_root)

                yield _LeanFile(
                    abs_path=path,
                    file_path=rel,
                    module_path=module_path,
                    origin=origin,
                )
                produced += 1
                if produced >= max_files:
                    return

    @staticmethod
    def _normalize_path_filter(repo_root: Path, raw: str | None) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None

        path = Path(text).expanduser()
        if path.is_absolute():
            resolved = path.resolve()
            try:
                return resolved.relative_to(repo_root).as_posix()
            except ValueError as exc:
                raise ValueError(f"path_filter resolves outside repo_root: {resolved}") from exc

        normalized = text.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if "." in normalized and "/" not in normalized and not normalized.endswith(".lean"):
            normalized = normalized.replace(".", "/")
        return normalized.strip("/")

    @staticmethod
    def _matches_path_filter(file_path: str, path_filter: str) -> bool:
        if not path_filter:
            return True
        normalized_file = file_path.strip("/")
        normalized_filter = path_filter.strip("/")
        return normalized_file == normalized_filter or normalized_file.startswith(
            normalized_filter + "/"
        )

    @staticmethod
    def _strip_line_comment(line: str) -> str:
        if "--" not in line:
            return line
        return line.split("--", 1)[0]

    def _extract_import_modules(self, lines: list[str]) -> list[str]:
        modules: list[str] = []
        for line in lines:
            clean = self._strip_line_comment(line).strip()
            if not clean:
                continue
            m = _IMPORT_RE.match(clean)
            if not m:
                continue
            rest = m.group(2).strip()
            if not rest:
                continue
            tokens = [tok for tok in rest.split() if tok]
            if tokens and tokens[0] == "all":
                tokens = tokens[1:]
            modules.extend(tokens)
        return modules

    def _extract_import_edges(self, lines: list[str]) -> list[tuple[str, int]]:
        edges: list[tuple[str, int]] = []
        for idx, line in enumerate(lines, start=1):
            clean = self._strip_line_comment(line).strip()
            if not clean:
                continue
            m = _IMPORT_RE.match(clean)
            if not m:
                continue
            rest = m.group(2).strip()
            tokens = [tok for tok in rest.split() if tok]
            if tokens and tokens[0] == "all":
                tokens = tokens[1:]
            for token in tokens:
                edges.append((token, idx))
        return edges

    def _extract_declarations(
        self,
        *,
        lines: list[str],
        file_path: str,
        module_path: str | None,
    ) -> list[_DeclarationRecord]:
        records: list[_DeclarationRecord] = []
        namespace_stack: list[str] = []

        for idx, line in enumerate(lines, start=1):
            ns_match = _NAMESPACE_RE.match(line)
            if ns_match:
                name = ns_match.group(1)
                if namespace_stack:
                    full = f"{namespace_stack[-1]}.{name}"
                else:
                    full = name
                namespace_stack.append(full)
                continue

            if _END_RE.match(line):
                if namespace_stack:
                    namespace_stack.pop()
                continue

            decl_match = _DECL_RE.match(line)
            if not decl_match:
                continue

            kind = decl_match.group("kind")
            rest = decl_match.group("rest").strip()
            visibility = None
            mods = decl_match.group("mods") or ""
            if "private" in mods.split():
                visibility = "private"
            elif "protected" in mods.split():
                visibility = "protected"
            else:
                visibility = "public"

            name_match = re.match(r"([A-Za-z_][A-Za-z0-9_'.]*)", rest)
            if not name_match:
                continue
            short_name = name_match.group(1)

            if "." in short_name:
                full_name = short_name
            elif namespace_stack:
                full_name = f"{namespace_stack[-1]}.{short_name}"
            else:
                full_name = short_name

            records.append(
                _DeclarationRecord(
                    full_name=full_name,
                    short_name=short_name.rsplit(".", 1)[-1],
                    decl_kind=kind,
                    file_path=file_path,
                    module_path=module_path,
                    line_start=idx,
                    line_end=None,
                    header_preview=line.strip(),
                    visibility=visibility,
                )
            )

        return records

    def _extract_scope_cmds(
        self,
        *,
        lines: list[str],
        file_path: str,
        module_path: str | None,
    ) -> list[_ScopeRecord]:
        records: list[_ScopeRecord] = []
        for idx, line in enumerate(lines, start=1):
            stripped = self._strip_line_comment(line).strip()
            if not stripped:
                continue

            m = _NAMESPACE_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="namespace",
                        target=m.group(1),
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

            m = _SECTION_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="section",
                        target=(m.group(1) or "").strip() or None,
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

            m = _OPEN_SCOPED_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="open_scoped",
                        target=m.group(1).strip(),
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

            m = _OPEN_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="open",
                        target=m.group(1).strip(),
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

            m = _EXPORT_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="export",
                        target=m.group(1).strip(),
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

            m = _ATTRIBUTE_RE.match(stripped)
            if m:
                records.append(
                    _ScopeRecord(
                        scope_kind="attribute",
                        target=m.group(1).strip(),
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                    )
                )
                continue

        return records

    def _extract_doc_blocks(self, lines: list[str]) -> list[_DocBlock]:
        blocks: list[_DocBlock] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            marker = None
            kind = None
            if "/--" in line:
                marker = "/--"
                kind = "decl_doc"
            elif "/-!" in line:
                marker = "/-!"
                kind = "bang_doc"
            elif "/-" in line:
                marker = "/-"
                kind = "comment"

            if marker is None or kind is None:
                i += 1
                continue

            start = i
            text_lines = [line]
            if "-/" in line and line.index("-/") > line.index(marker):
                end = i
            else:
                j = i + 1
                end = i
                while j < len(lines):
                    text_lines.append(lines[j])
                    if "-/" in lines[j]:
                        end = j
                        break
                    j += 1
                if j >= len(lines):
                    end = len(lines) - 1
                i = end

            blocks.append(
                _DocBlock(
                    kind=kind,
                    text="\n".join(text_lines),
                    line_start=start + 1,
                    line_end=end + 1,
                )
            )
            i += 1

        return blocks

    def _extract_text_hits(
        self,
        *,
        lines: list[str],
        file_path: str,
        module_path: str | None,
        query: str,
        text_match: str,
        scopes: tuple[str, ...],
        context_lines: int,
    ) -> list[LocalTextFindItem]:
        scope_set = set(scopes)
        hits: list[LocalTextFindItem] = []

        docs = self._extract_doc_blocks(lines)
        doc_first_bang_idx: int | None = None
        for idx, block in enumerate(docs):
            if block.kind == "bang_doc":
                doc_first_bang_idx = idx
                break

        if "module_doc" in scope_set or "section_doc" in scope_set or "decl_doc" in scope_set:
            for idx, block in enumerate(docs):
                scope = None
                if block.kind == "decl_doc" and "decl_doc" in scope_set:
                    scope = "decl_doc"
                elif block.kind == "bang_doc":
                    if doc_first_bang_idx is not None and idx == doc_first_bang_idx:
                        if "module_doc" in scope_set:
                            scope = "module_doc"
                    elif "section_doc" in scope_set:
                        scope = "section_doc"
                elif block.kind == "comment" and "comment" in scope_set:
                    scope = "comment"

                if scope is None:
                    continue
                if not self._match_by_mode(block.text, query, text_match):
                    continue
                hits.append(
                    LocalTextFindItem(
                        scope=scope,
                        file_path=file_path,
                        module_path=module_path,
                        line_start=block.line_start,
                        line_end=block.line_end,
                        snippet=self._make_context_snippet(
                            lines=lines,
                            line_start=block.line_start,
                            line_end=block.line_end,
                            context_lines=context_lines,
                        ),
                    )
                )

        need_decl = "decl_header" in scope_set or "decl_sig" in scope_set
        if need_decl:
            decls = self._extract_declarations(lines=lines, file_path=file_path, module_path=module_path)
            for rec in decls:
                if not self._match_by_mode(rec.header_preview, query, text_match):
                    continue
                if "decl_header" in scope_set:
                    hits.append(
                        LocalTextFindItem(
                            scope="decl_header",
                            file_path=file_path,
                            module_path=module_path,
                            line_start=rec.line_start,
                            line_end=rec.line_start,
                            snippet=self._make_context_snippet(
                                lines=lines,
                                line_start=rec.line_start,
                                line_end=rec.line_start,
                                context_lines=context_lines,
                            ),
                        )
                    )
                if "decl_sig" in scope_set:
                    hits.append(
                        LocalTextFindItem(
                            scope="decl_sig",
                            file_path=file_path,
                            module_path=module_path,
                            line_start=rec.line_start,
                            line_end=rec.line_start,
                            snippet=self._make_context_snippet(
                                lines=lines,
                                line_start=rec.line_start,
                                line_end=rec.line_start,
                                context_lines=context_lines,
                            ),
                        )
                    )

        if "body" in scope_set or "comment" in scope_set:
            for idx, line in enumerate(lines, start=1):
                scope = "comment" if line.lstrip().startswith("--") else "body"
                if scope not in scope_set:
                    continue
                if not self._match_by_mode(line, query, text_match):
                    continue
                hits.append(
                    LocalTextFindItem(
                        scope=scope,
                        file_path=file_path,
                        module_path=module_path,
                        line_start=idx,
                        line_end=idx,
                        snippet=self._make_context_snippet(
                            lines=lines,
                            line_start=idx,
                            line_end=idx,
                            context_lines=context_lines,
                        ),
                    )
                )

        return hits

    @staticmethod
    def _infer_line_scope(line: str) -> str:
        stripped = line.strip()
        if _IMPORT_RE.match(stripped):
            return "import"
        if _DECL_RE.match(stripped):
            return "decl_header"
        if (
            _NAMESPACE_RE.match(stripped)
            or _SECTION_RE.match(stripped)
            or _OPEN_SCOPED_RE.match(stripped)
            or _OPEN_RE.match(stripped)
            or _EXPORT_RE.match(stripped)
            or _ATTRIBUTE_RE.match(stripped)
        ):
            return "scope_cmd"
        if stripped.startswith("--"):
            return "comment"
        return "body"

    @staticmethod
    def _build_symbol_pattern(symbol: str) -> re.Pattern[str]:
        esc = re.escape(symbol)
        return re.compile(rf"(?<![A-Za-z0-9_']){esc}(?![A-Za-z0-9_'])")

    @staticmethod
    def _match_text(text: str, query: str, mode: str) -> bool:
        t = text.casefold()
        q = query.casefold()
        if mode == "exact":
            return t == q
        if mode == "suffix":
            return t.endswith(q)
        return t.startswith(q)

    @staticmethod
    def _match_by_mode(text: str, query: str, mode: str) -> bool:
        if not query:
            return True
        if mode == "regex":
            try:
                return re.search(query, text, flags=re.IGNORECASE) is not None
            except re.error:
                return False

        if mode == "word":
            pattern = re.compile(rf"\b{re.escape(query)}\b", flags=re.IGNORECASE)
            return pattern.search(text) is not None

        return query.casefold() in text.casefold()

    @staticmethod
    def _make_context_snippet(
        *,
        lines: list[str],
        line_start: int,
        line_end: int,
        context_lines: int,
    ) -> str:
        start_idx = max(0, line_start - 1 - context_lines)
        end_idx = min(len(lines), line_end + context_lines)
        return "\n".join(
            f"{idx + 1:>5} | {lines[idx]}" for idx in range(start_idx, end_idx)
        )


__all__ = ["SearchNavServiceImpl"]
