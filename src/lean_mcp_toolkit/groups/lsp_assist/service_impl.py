"""lsp_assist service implementation.

This group adapts additional Lean LSP MCP tools and adds a few toolkit-native
helpers that reuse the same path normalization and LSP client-management layer.

Reference projects:
- lean-lsp-mcp (project-numina fork): https://github.com/project-numina/lean-lsp-mcp
- lean-lsp-mcp upstream: https://github.com/oOo0oOo/lean-lsp-mcp

Method mapping:
- ``run_completions`` -> ``lean_completions``
- ``run_declaration_file`` -> ``lean_declaration_file``
- ``run_multi_attempt`` -> ``lean_multi_attempt``
- ``run_declaration_soundness`` -> toolkit-native exact declaration soundness helper
- ``run_declaration_soundness_batch`` -> batched exact declaration soundness helper
- ``run_compiled_declaration_batch`` -> batched Environment identity/provenance helper
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.parse import unquote, urlparse
import uuid

from ...backends.lean.path import LeanPath
from ...backends.lean.path import resolve_project_root
from ...backends.lsp import LeanLSPClientManager
from ...config import ToolkitConfig
from ...contracts.lsp_assist import (
    AttemptResult,
    CompiledDeclarationResult,
    CompiledDeclarationTarget,
    CompletionItem,
    DeclarationSoundnessResult,
    DeclarationSoundnessTarget,
    DiagnosticMessage,
    LspCompletionsRequest,
    LspCompletionsResponse,
    LspCompiledDeclarationBatchRequest,
    LspCompiledDeclarationBatchResponse,
    LspDeclarationSoundnessBatchRequest,
    LspDeclarationSoundnessBatchResponse,
    LspDeclarationSoundnessRequest,
    LspDeclarationSoundnessResponse,
    LspDeclarationFileRequest,
    LspDeclarationFileResponse,
    LspMultiAttemptRequest,
    LspMultiAttemptResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    Position,
    Range,
    SourceWarning,
)
from ...core.services import LspAssistService

_AXIOM_DEPENDS_RE = re.compile(
    r"^'(?P<declaration>.+?)'\s+depends on axioms:\s*\[(?P<axioms>.*?)\]\s*$",
    re.DOTALL,
)
_AXIOM_NONE_RE = re.compile(
    r"^'(?P<declaration>.+?)'\s+does not depend on any axioms\s*$"
)
_COMPILED_DECLARATION_MARKER = "__TOOLKIT_COMPILED_DECL__"

_WARNING_PATTERNS: tuple[str, ...] = (
    r"set_option\s+debug\.",
    r"\bunsafe\b",
    r"@\[implemented_by\b",
    r"@\[extern\b",
    r"\bopaque\b",
    r"local\s+instance\b",
    r"local\s+notation\b",
    r"local\s+macro_rules\b",
    r"scoped\s+notation\b",
    r"scoped\s+instance\b",
    r"@\[csimp\b",
    r"import\s+Lean\.Elab\b",
    r"import\s+Lean\.Meta\b",
)
_COMBINED_WARNING_PATTERN = "|".join(f"(?:{p})" for p in _WARNING_PATTERNS)

_COMPLETION_KIND: dict[int, str] = {
    1: "text",
    2: "method",
    3: "function",
    4: "constructor",
    5: "field",
    6: "variable",
    7: "class",
    8: "interface",
    9: "module",
    10: "property",
    11: "unit",
    12: "value",
    13: "enum",
    14: "keyword",
    15: "snippet",
    16: "color",
    17: "file",
    18: "reference",
    19: "folder",
    20: "enum_member",
    21: "constant",
    22: "struct",
    23: "event",
    24: "operator",
    25: "type_parameter",
}


@dataclass(slots=True)
class LspAssistServiceImpl(LspAssistService):
    """Service adapter for LSP-assisted proof development helpers."""

    config: ToolkitConfig
    lsp_client_manager: LeanLSPClientManager

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        lsp_client_manager: LeanLSPClientManager | None = None,
    ):
        self.config = config
        self.lsp_client_manager = lsp_client_manager or LeanLSPClientManager(
            backend_config=config.backends.lsp
        )

    def run_completions(self, req: LspCompletionsRequest) -> LspCompletionsResponse:
        """Adapt the upstream ``lean_completions`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            raw = client.get_completions(rel_path, req.line - 1, req.column - 1)
            items = self._map_completion_items(raw)

            limit = (
                req.max_completions
                if req.max_completions is not None
                else self.config.lsp_assist.default_max_completions
            )
            limit = max(1, limit)
            sorted_items = self._sort_completion_items(
                content=content,
                line=req.line,
                column=req.column,
                items=items,
            )[:limit]
            return LspCompletionsResponse(
                success=True,
                error_message=None,
                items=tuple(sorted_items),
                count=len(sorted_items),
            )
        except Exception as exc:
            return LspCompletionsResponse(
                success=False,
                error_message=str(exc),
                items=tuple(),
                count=0,
            )

    def run_declaration_file(
        self,
        req: LspDeclarationFileRequest,
    ) -> LspDeclarationFileResponse:
        """Adapt the upstream ``lean_declaration_file`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            symbol = req.symbol.strip()
            if not symbol:
                raise ValueError("symbol is required")
            if (req.line is None) ^ (req.column is None):
                raise ValueError("line and column must be provided together")

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            file_content = client.get_file_content(rel_path)

            source_pos = self._resolve_symbol_position(
                content=file_content,
                symbol=symbol,
                line=req.line,
                column=req.column,
            )
            if source_pos is None:
                raise ValueError(f"symbol `{symbol}` not found in source file")

            line0, col0 = source_pos
            targets = client.get_declarations(rel_path, line0, col0) or []
            if not targets:
                targets = client.get_definitions(rel_path, line0, col0) or []
            if not targets:
                raise ValueError(f"no declaration target found for symbol `{symbol}`")

            target = targets[0]
            target_uri = target.get("targetUri") or target.get("uri")
            if not isinstance(target_uri, str) or not target_uri.strip():
                raise ValueError("LSP response missing target uri")
            target_path = self._uri_to_path(target_uri)
            if target_path is None:
                raise ValueError(f"unsupported target uri: {target_uri}")

            include_content = (
                req.include_file_content
                if req.include_file_content is not None
                else self.config.lsp_assist.declaration_file_include_content_default
            )
            content: str | None = None
            if include_content:
                try:
                    content = target_path.read_text(encoding="utf-8")
                except Exception:
                    content = None

            return LspDeclarationFileResponse(
                success=True,
                error_message=None,
                source_pos=Position(line=line0 + 1, column=col0 + 1),
                target_file_path=str(target_path.resolve()),
                target_file_uri=target_uri,
                target_range=self._range_from_lsp(target.get("targetRange") or target.get("range")),
                target_selection_range=self._range_from_lsp(target.get("targetSelectionRange")),
                content=content,
            )
        except Exception as exc:
            return LspDeclarationFileResponse(
                success=False,
                error_message=str(exc),
                source_pos=None,
                target_file_path=None,
                target_file_uri=None,
                target_range=None,
                target_selection_range=None,
                content=None,
            )

    def run_multi_attempt(self, req: LspMultiAttemptRequest) -> LspMultiAttemptResponse:
        """Adapt the upstream ``lean_multi_attempt`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            snippets = [item.rstrip("\n") for item in req.snippets if item.strip()]
            if not snippets:
                raise ValueError("snippets must be a non-empty list")

            max_attempts = (
                req.max_attempts
                if req.max_attempts is not None
                else self.config.lsp_assist.multi_attempt_default_max_attempts
            )
            if max_attempts is not None and max_attempts > 0:
                snippets = snippets[:max_attempts]
            hard_limit = max(1, self.config.lsp_assist.multi_attempt_max_snippets_hard_limit)
            snippets = snippets[:hard_limit]

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            original_content = client.get_file_content(rel_path)
            lines = original_content.splitlines()
            if req.line < 1 or req.line > len(lines):
                raise ValueError("line out of range for file content")

            out: list[AttemptResult] = []
            try:
                for snippet in snippets:
                    payload = f"{snippet}\n"
                    change = self._new_document_content_change(
                        payload=payload,
                        start_line=req.line - 1,
                        start_col=0,
                        end_line=req.line,
                        end_col=0,
                    )
                    client.update_file(rel_path, [change])

                    raw_diag = client.get_diagnostics(
                        rel_path,
                        start_line=req.line - 1,
                        end_line=req.line - 1,
                        inactivity_timeout=float(
                            self.config.backends.lsp.diagnostics_timeout_seconds
                        ),
                    )
                    diagnostics = tuple(
                        self._map_diagnostic_message(item)
                        for item in self._extract_diagnostics_list(raw_diag)
                    )
                    raw_goal = client.get_goal(rel_path, req.line - 1, max(0, len(snippet)))
                    goals = self._extract_goals(raw_goal)
                    has_error = any(
                        (diag.severity or "").strip().lower() == "error"
                        for diag in diagnostics
                    )
                    out.append(
                        AttemptResult(
                            snippet=snippet,
                            goals=goals,
                            diagnostics=diagnostics,
                            attempt_success=(not has_error),
                            goal_count=len(goals),
                        )
                    )
            finally:
                try:
                    client.update_file_content(rel_path, original_content)
                except Exception:
                    pass
                try:
                    client.open_file(rel_path, force_reopen=True)
                except Exception:
                    pass

            any_success = any(item.attempt_success for item in out)
            return LspMultiAttemptResponse(
                success=True,
                error_message=None,
                items=tuple(out),
                count=len(out),
                any_success=any_success,
            )
        except Exception as exc:
            return LspMultiAttemptResponse(
                success=False,
                error_message=str(exc),
                items=tuple(),
                count=0,
                any_success=False,
            )

    def run_snippet(self, req: LspRunSnippetRequest) -> LspRunSnippetResponse:
        """Run a temporary Lean snippet inside the current project."""
        project_root: Path | None = None
        snippet_path: Path | None = None
        rel_path: str | None = None
        client: Any | None = None
        recycle_client = False
        try:
            project_root = self._resolve_project_root(req.project_root)
            code = req.code
            if not code.strip():
                raise ValueError("code is required")
            max_chars = max(1, self.config.lsp_core.run_snippet_max_code_chars)
            if len(code) > max_chars:
                raise ValueError(f"code exceeds max length: {len(code)} > {max_chars}")

            rel_path = f"_mcp_snippet_{uuid.uuid4().hex}.lean"
            snippet_path = (project_root / rel_path).resolve()
            snippet_path.write_text(code, encoding="utf-8")

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)

            inactivity_timeout = float(self._resolve_run_snippet_timeout_seconds(req.timeout_seconds))
            raw_diag = self._get_diagnostics_with_hard_timeout(
                client=client,
                rel_path=rel_path,
                timeout_seconds=inactivity_timeout,
            )
            diagnostics = tuple(
                self._map_diagnostic_message(item)
                for item in self._extract_diagnostics_list(raw_diag)
            )
            error_count = 0
            warning_count = 0
            info_count = 0
            for item in diagnostics:
                sev = (item.severity or "").strip().lower()
                if sev == "error":
                    error_count += 1
                elif sev == "warning":
                    warning_count += 1
                else:
                    info_count += 1

            return LspRunSnippetResponse(
                success=(error_count == 0),
                error_message=None,
                diagnostics=diagnostics,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
            )
        except Exception as exc:
            recycle_client = client is not None and project_root is not None
            return LspRunSnippetResponse(
                success=False,
                error_message=str(exc),
                diagnostics=tuple(),
                error_count=0,
                warning_count=0,
                info_count=0,
            )
        finally:
            if recycle_client and project_root is not None:
                try:
                    self.lsp_client_manager.recycle_client(project_root)
                except Exception:
                    pass
            elif client is not None and rel_path is not None:
                try:
                    client.close_files([rel_path])
                except Exception:
                    pass
            if snippet_path is not None:
                try:
                    snippet_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _resolve_run_snippet_timeout_seconds(self, requested_timeout: int | None) -> int:
        timeout_seconds = (
            requested_timeout
            if requested_timeout is not None
            else self.config.lsp_core.run_snippet_default_timeout_seconds
        )
        if timeout_seconds is None or timeout_seconds <= 0:
            timeout_seconds = self.config.backends.lsp.diagnostics_timeout_seconds

        max_timeout = max(1, int(self.config.lsp_core.run_snippet_max_timeout_seconds))
        return min(max(1, int(timeout_seconds)), max_timeout)

    @staticmethod
    def _get_diagnostics_with_hard_timeout(
        *,
        client: Any,
        rel_path: str,
        timeout_seconds: float,
    ) -> Any:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="toolkit-lsp-snippet")
        future = executor.submit(
            client.get_diagnostics,
            rel_path,
            None,
            None,
            timeout_seconds,
        )
        try:
            return future.result(timeout=max(1.0, timeout_seconds + 1.0))
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"LSP diagnostics timed out after {timeout_seconds:.1f}s") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def run_declaration_soundness(
        self,
        req: LspDeclarationSoundnessRequest,
    ) -> LspDeclarationSoundnessResponse:
        """Check one exact declaration through the batch implementation."""
        batch = self.run_declaration_soundness_batch(
            LspDeclarationSoundnessBatchRequest(
                project_root=req.project_root,
                declarations=(
                    DeclarationSoundnessTarget(
                        module=req.module,
                        declaration_name=req.declaration_name,
                        source_file_path=req.source_file_path,
                    ),
                ),
                scan_source=req.scan_source,
            )
        )
        if batch.items:
            item = batch.items[0]
            if batch.success and item.success:
                return LspDeclarationSoundnessResponse(**item.__dict__)
            return LspDeclarationSoundnessResponse(
                module=item.module,
                declaration_name=item.declaration_name,
                success=False,
                source_file_path=item.source_file_path,
                error_message=item.error_message or batch.error_message,
            )
        return LspDeclarationSoundnessResponse(
            module=req.module,
            declaration_name=req.declaration_name,
            success=False,
            source_file_path=req.source_file_path,
            error_message=batch.error_message or "declaration soundness check failed",
        )

    def run_declaration_soundness_batch(
        self,
        req: LspDeclarationSoundnessBatchRequest,
    ) -> LspDeclarationSoundnessBatchResponse:
        """Check exact declarations in one temporary ``#print axioms`` LSP file."""
        project_root: Path | None = None
        verify_path: Path | None = None
        rel_path: str | None = None
        client: Any | None = None
        recycle_client = False
        try:
            project_root = self._resolve_project_root(req.project_root)
            if not req.declarations:
                raise ValueError("declarations must be a non-empty list")

            scan_source = (
                req.scan_source
                if req.scan_source is not None
                else self.config.lsp_assist.declaration_soundness_scan_source_default
            )
            normalized: list[DeclarationSoundnessTarget] = []
            declaration_names: set[str] = set()
            module_names: list[str] = []
            for target in req.declarations:
                module_name = LeanPath.from_dot(target.module).dot
                declaration_name = target.declaration_name.strip()
                if not declaration_name:
                    raise ValueError("declaration_name is required")
                if any(char.isspace() for char in declaration_name) or any(
                    char in declaration_name for char in "#;\n\r"
                ):
                    raise ValueError(
                        f"declaration_name is not a safe exact Lean name: {declaration_name!r}"
                    )
                if declaration_name in declaration_names:
                    raise ValueError(f"duplicate declaration_name: {declaration_name}")
                declaration_names.add(declaration_name)
                source_file_path = None
                if target.source_file_path is not None:
                    source_file_path = self._normalize_file_path(
                        project_root=project_root,
                        file_path=target.source_file_path,
                    )
                if scan_source and source_file_path is None:
                    raise ValueError(
                        "source_file_path is required when scan_source is true"
                    )
                normalized.append(
                    DeclarationSoundnessTarget(
                        module=module_name,
                        declaration_name=declaration_name,
                        source_file_path=source_file_path,
                    )
                )
                if module_name not in module_names:
                    module_names.append(module_name)

            lines = [*(f"import {module_name}" for module_name in module_names), ""]
            lines.extend(
                f"#print axioms {target.declaration_name}" for target in normalized
            )
            rel_path = f"_mcp_decl_soundness_{uuid.uuid4().hex}.lean"
            verify_path = (project_root / rel_path).resolve()
            verify_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            raw_diag = self._get_diagnostics_with_hard_timeout(
                client=client,
                rel_path=rel_path,
                timeout_seconds=float(self.config.backends.lsp.diagnostics_timeout_seconds),
            )
            diagnostics = self._extract_diagnostics_list(raw_diag)
            error_messages = [
                str(item.get("message") or item.get("data") or "")
                for item in diagnostics
                if self._severity_text(item.get("severity")) == "error"
            ]
            reports = self._parse_axiom_reports_from_diagnostics(diagnostics)
            requested_names = {target.declaration_name for target in normalized}
            unexpected_names = sorted(name for name in reports if name not in requested_names)
            batch_errors = [msg for msg in error_messages if msg.strip()]
            if unexpected_names:
                batch_errors.append(
                    "unexpected axiom reports for: "
                    + ", ".join(repr(name) for name in unexpected_names)
                )

            warnings_by_file: dict[str, tuple[SourceWarning, ...]] = {}
            if scan_source:
                for target in normalized:
                    assert target.source_file_path is not None
                    if target.source_file_path not in warnings_by_file:
                        warnings_by_file[target.source_file_path] = (
                            self._scan_source_warnings(
                                (project_root / target.source_file_path).resolve()
                            )
                        )

            items: list[DeclarationSoundnessResult] = []
            fallback_error = "; ".join(batch_errors)
            for target in normalized:
                matching_reports = reports.get(target.declaration_name, [])
                warnings = warnings_by_file.get(target.source_file_path or "", tuple())
                if len(matching_reports) == 1:
                    axioms = matching_reports[0]
                    items.append(
                        DeclarationSoundnessResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=True,
                            source_file_path=target.source_file_path,
                            axioms=axioms,
                            warnings=warnings,
                            axiom_count=len(axioms),
                            warning_count=len(warnings),
                        )
                    )
                    continue
                if not matching_reports:
                    item_error = (
                        fallback_error
                        or f"axiom report not found for declaration '{target.declaration_name}'"
                    )
                else:
                    item_error = (
                        f"expected one axiom report for declaration '{target.declaration_name}', "
                        f"received {len(matching_reports)}"
                    )
                items.append(
                    DeclarationSoundnessResult(
                        module=target.module,
                        declaration_name=target.declaration_name,
                        success=False,
                        source_file_path=target.source_file_path,
                        error_message=item_error,
                        warnings=warnings,
                        warning_count=len(warnings),
                    )
                )

            success_count = sum(item.success for item in items)
            failure_count = len(items) - success_count
            success = failure_count == 0 and not batch_errors
            error_message = None
            if not success:
                error_message = (
                    "; ".join(batch_errors)
                    if batch_errors
                    else f"{failure_count} of {len(items)} declaration soundness checks failed"
                )
            return LspDeclarationSoundnessBatchResponse(
                success=success,
                error_message=error_message,
                items=tuple(items),
                count=len(items),
                success_count=success_count,
                failure_count=failure_count,
            )
        except Exception as exc:
            recycle_client = client is not None and project_root is not None
            return LspDeclarationSoundnessBatchResponse(
                success=False,
                error_message=str(exc),
                items=tuple(),
                count=0,
                success_count=0,
                failure_count=0,
            )
        finally:
            if recycle_client and project_root is not None:
                try:
                    self.lsp_client_manager.recycle_client(project_root)
                except Exception:
                    pass
            elif client is not None and rel_path is not None:
                try:
                    client.close_files([rel_path])
                except Exception:
                    pass
            if verify_path is not None:
                try:
                    verify_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def run_compiled_declaration_batch(
        self,
        req: LspCompiledDeclarationBatchRequest,
    ) -> LspCompiledDeclarationBatchResponse:
        """Inspect exact imported constants through one compiler-backed LSP probe."""
        project_root: Path | None = None
        verify_path: Path | None = None
        rel_path: str | None = None
        client: Any | None = None
        recycle_client = False
        try:
            project_root = self._resolve_project_root(req.project_root)
            if not req.declarations:
                raise ValueError("declarations must be a non-empty list")

            normalized: list[CompiledDeclarationTarget] = []
            exact_refs: set[tuple[str, str]] = set()
            module_names: list[str] = []
            for target in req.declarations:
                module_name = LeanPath.from_dot(target.module).dot
                declaration_name = target.declaration_name.strip()
                if not declaration_name:
                    raise ValueError("declaration_name is required")
                if any(char.isspace() for char in declaration_name) or any(
                    char in declaration_name for char in "#;`\n\r"
                ):
                    raise ValueError(
                        f"declaration_name is not a safe exact Lean name: {declaration_name!r}"
                    )
                exact_ref = (module_name, declaration_name)
                if exact_ref in exact_refs:
                    raise ValueError(
                        "duplicate compiled declaration target: "
                        f"{module_name}::{declaration_name}"
                    )
                exact_refs.add(exact_ref)
                normalized.append(
                    CompiledDeclarationTarget(
                        module=module_name,
                        declaration_name=declaration_name,
                    )
                )
                if module_name not in module_names:
                    module_names.append(module_name)

            provenance_error_message: str | None = None
            include_to_additive = req.include_to_additive_provenance
            if include_to_additive and not self._project_has_to_additive(project_root):
                include_to_additive = False
                provenance_error_message = (
                    "to_additive provenance is unavailable because the project does not expose "
                    "Mathlib.Tactic.Translate.ToAdditive"
                )

            lines = [*(f"import {module_name}" for module_name in module_names)]
            lines.extend(["import Lean.Meta.Eqns", "import Lean.ProjFns"])
            if include_to_additive:
                lines.append("import Mathlib.Tactic.Translate.ToAdditive")
            lines.extend(["", "open Lean Meta", "", "run_meta do", "  let env ← getEnv"])
            if include_to_additive:
                lines.extend(
                    [
                        "  let translations :=",
                        "    (SimplePersistentEnvExtension.getState "
                        "Mathlib.Tactic.ToAdditive.translations env).get",
                    ]
                )
            targets = ", ".join(
                f"({index}, `{target.declaration_name})"
                for index, target in enumerate(normalized)
            )
            lines.extend(
                [
                    f"  let targets : Array (Nat × Name) := #[{targets}]",
                    "  for (index, target) in targets do",
                    "    match env.find? target with",
                    "    | none =>",
                    "      let payload := Json.mkObj [",
                    '        ("index", toJson index),',
                    '        ("declaration_name", toJson target.toString),',
                    '        ("found", toJson false)]',
                    f'      logInfo m!"{_COMPILED_DECLARATION_MARKER}{{payload.compress}}"',
                    "    | some info =>",
                    "      let kind := match info with",
                    '        | .axiomInfo _ => "axiom"',
                    '        | .defnInfo _ => "definition"',
                    '        | .thmInfo _ => "theorem"',
                    '        | .opaqueInfo _ => "opaque"',
                    '        | .quotInfo _ => "quotient"',
                    '        | .inductInfo _ => "inductive"',
                    '        | .ctorInfo _ => "constructor"',
                    '        | .recInfo _ => "recursor"',
                    "      let signature := toString (← ppExpr info.type)",
                    "      let owner := env.getModuleIdxFor? target |>.map fun idx =>",
                    "        env.header.moduleNames[idx]!",
                    "      let equationSource ← do",
                    "        let .thmInfo theoremInfo := info | pure none",
                    "        let some (_, lhs, _) := theoremInfo.type.getForallBody.eq? | pure none",
                    "        let some candidate := lhs.getAppFn.constName? | pure none",
                    "        let some equations ← Meta.getEqnsFor? candidate | pure none",
                    "        if equations.contains target then pure (some candidate) else pure none",
                    "      let coreProvenance : Option (String × Name) := match info with",
                    '        | .ctorInfo ctorInfo => some ("inductive_constructor", ctorInfo.induct)',
                    '        | .recInfo recInfo => some ("inductive_recursor", recInfo.getMajorInduct)',
                    "        | _ => match env.getProjectionStructureName? target with",
                    '          | some structureName => some ("structure_projection", structureName)',
                    '          | none => equationSource.map fun source => ("equation_theorem", source)',
                ]
            )
            if include_to_additive:
                lines.extend(
                    [
                        "      let toAdditiveSources := translations.toList.filterMap fun item =>",
                        "        if item.2.translation == target then some item.1.toString else none",
                    ]
                )
            else:
                lines.append("      let toAdditiveSources : List String := []")
            lines.extend(
                [
                    "      let payload := Json.mkObj [",
                    '        ("index", toJson index),',
                    '        ("declaration_name", toJson target.toString),',
                    '        ("found", toJson true),',
                    '        ("declaration_kind", toJson kind),',
                    '        ("signature", toJson signature),',
                    '        ("universe_count", toJson info.levelParams.length),',
                    '        ("owner_module", owner.map (toJson ·.toString) |>.getD Json.null),',
                    '        ("core_generation_kind", coreProvenance.map (toJson ·.1) |>.getD Json.null),',
                    '        ("core_generator_declaration", coreProvenance.map (toJson ·.2.toString) |>.getD Json.null),',
                    '        ("to_additive_sources", toJson toAdditiveSources)]',
                    f'      logInfo m!"{_COMPILED_DECLARATION_MARKER}{{payload.compress}}"',
                ]
            )

            rel_path = f"_mcp_compiled_decls_{uuid.uuid4().hex}.lean"
            verify_path = (project_root / rel_path).resolve()
            verify_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            raw_diag = self._get_diagnostics_with_hard_timeout(
                client=client,
                rel_path=rel_path,
                timeout_seconds=float(self.config.backends.lsp.diagnostics_timeout_seconds),
            )
            diagnostics = self._extract_diagnostics_list(raw_diag)
            error_messages = [
                str(item.get("message") or item.get("data") or "")
                for item in diagnostics
                if self._severity_text(item.get("severity")) == "error"
            ]
            reports, report_errors = self._parse_compiled_declaration_reports(diagnostics)
            batch_errors = [message for message in [*error_messages, *report_errors] if message]
            unexpected_indexes = sorted(set(reports) - set(range(len(normalized))))
            if unexpected_indexes:
                batch_errors.append(
                    "unexpected compiled declaration report indexes: "
                    + ", ".join(str(index) for index in unexpected_indexes)
                )

            items: list[CompiledDeclarationResult] = []
            for index, target in enumerate(normalized):
                report = reports.get(index)
                if report is None:
                    items.append(
                        CompiledDeclarationResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=False,
                            error_message=(
                                "; ".join(batch_errors)
                                or "compiled declaration report was not returned"
                            ),
                            provenance_error_message=provenance_error_message,
                        )
                    )
                    continue
                if report.get("declaration_name") != target.declaration_name:
                    items.append(
                        CompiledDeclarationResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=False,
                            error_message="compiled declaration report identity mismatch",
                            provenance_error_message=provenance_error_message,
                        )
                    )
                    continue
                if report.get("found") is not True:
                    items.append(
                        CompiledDeclarationResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=False,
                            error_message=(
                                f"compiled declaration not found: {target.declaration_name}"
                            ),
                            provenance_error_message=provenance_error_message,
                        )
                    )
                    continue
                kind = str(report.get("declaration_kind") or "")
                signature = str(report.get("signature") or "")
                owner_module = report.get("owner_module")
                sources = report.get("to_additive_sources")
                core_generation_kind = report.get("core_generation_kind")
                core_generator_declaration = report.get(
                    "core_generator_declaration"
                )
                if not kind or not signature or not isinstance(sources, list):
                    items.append(
                        CompiledDeclarationResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=False,
                            error_message="compiled declaration report is incomplete",
                            provenance_error_message=provenance_error_message,
                        )
                    )
                    continue
                core_fields = (core_generation_kind, core_generator_declaration)
                if (core_fields[0] is None) != (core_fields[1] is None) or any(
                    value is not None and not isinstance(value, str)
                    for value in core_fields
                ):
                    items.append(
                        CompiledDeclarationResult(
                            module=target.module,
                            declaration_name=target.declaration_name,
                            success=False,
                            error_message="compiled declaration core provenance is incomplete",
                            provenance_error_message=provenance_error_message,
                        )
                    )
                    continue
                generation_kind: str | None = None
                generator_declaration: str | None = None
                item_provenance_error = provenance_error_message
                if len(sources) == 1 and isinstance(sources[0], str):
                    generation_kind = "to_additive"
                    generator_declaration = sources[0]
                elif len(sources) > 1:
                    item_provenance_error = (
                        "multiple to_additive sources map to the exact compiled declaration"
                    )
                if generation_kind is None and isinstance(
                    core_generation_kind, str
                ) and isinstance(core_generator_declaration, str):
                    generation_kind = core_generation_kind
                    generator_declaration = core_generator_declaration
                items.append(
                    CompiledDeclarationResult(
                        module=target.module,
                        declaration_name=target.declaration_name,
                        success=True,
                        owner_module=(
                            str(owner_module) if owner_module is not None else None
                        ),
                        declaration_kind=kind,
                        signature=signature,
                        universe_count=int(report.get("universe_count") or 0),
                        representation="compiled_reference",
                        reference_code=self._compiled_reference_code(
                            declaration_name=target.declaration_name,
                            declaration_kind=kind,
                        ),
                        generation_kind=generation_kind,
                        generator_declaration=generator_declaration,
                        provenance_error_message=item_provenance_error,
                    )
                )

            success_count = sum(item.success for item in items)
            failure_count = len(items) - success_count
            success = failure_count == 0 and not batch_errors
            error_message = None
            if not success:
                error_message = (
                    "; ".join(batch_errors)
                    if batch_errors
                    else f"{failure_count} of {len(items)} compiled declaration checks failed"
                )
            return LspCompiledDeclarationBatchResponse(
                success=success,
                error_message=error_message,
                items=tuple(items),
                count=len(items),
                success_count=success_count,
                failure_count=failure_count,
            )
        except Exception as exc:
            recycle_client = client is not None and project_root is not None
            return LspCompiledDeclarationBatchResponse(
                success=False,
                error_message=str(exc),
                items=tuple(),
                count=0,
                success_count=0,
                failure_count=0,
            )
        finally:
            if recycle_client and project_root is not None:
                try:
                    self.lsp_client_manager.recycle_client(project_root)
                except Exception:
                    pass
            elif client is not None and rel_path is not None:
                try:
                    client.close_files([rel_path])
                except Exception:
                    pass
            if verify_path is not None:
                try:
                    verify_path.unlink(missing_ok=True)
                except Exception:
                    pass

    @staticmethod
    def _project_has_to_additive(project_root: Path) -> bool:
        package_root = project_root / ".lake" / "packages" / "mathlib"
        source = package_root / "Mathlib" / "Tactic" / "Translate" / "ToAdditive.lean"
        olean = (
            package_root
            / ".lake"
            / "build"
            / "lib"
            / "lean"
            / "Mathlib"
            / "Tactic"
            / "Translate"
            / "ToAdditive.olean"
        )
        return source.is_file() or olean.is_file()

    @staticmethod
    def _compiled_reference_code(
        *, declaration_name: str, declaration_kind: str
    ) -> str | None:
        if declaration_kind != "theorem":
            return None
        rooted_name = declaration_name.removeprefix("_root_.")
        return f"#check _root_.{rooted_name}"

    def _resolve_project_root(self, project_root: str | None) -> Path:
        return resolve_project_root(
            project_root,
            default_project_root=self.config.server.default_project_root,
            allow_cwd_fallback=True,
        )

    def _normalize_file_path(self, *, project_root: Path, file_path: str) -> str:
        text = file_path.strip()
        if not text:
            raise ValueError("file_path is required")

        root = project_root.resolve()
        path_like = Path(text)

        if path_like.is_absolute():
            resolved = path_like.resolve()
            try:
                rel = resolved.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"absolute file_path outside project_root: {text}") from exc
            if not resolved.is_file() or resolved.suffix != ".lean":
                raise ValueError(f"file_path must be a .lean file: {text}")
            return rel.as_posix()

        if text.endswith(".lean"):
            rel = Path(text).as_posix().lstrip("/")
            abs_file = (root / rel).resolve()
            if not abs_file.exists() or not abs_file.is_file():
                raise ValueError(f"file_path does not exist: {text}")
            return rel

        candidate = (root / path_like).resolve()
        if candidate.exists():
            if not candidate.is_file() or candidate.suffix != ".lean":
                raise ValueError(f"file_path must be a .lean file: {text}")
            try:
                return candidate.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(f"file_path outside project_root: {text}") from exc

        module = LeanPath.from_dot(text)
        rel = module.to_rel_file()
        abs_file = (root / rel).resolve()
        if not abs_file.exists() or not abs_file.is_file():
            raise ValueError(f"dot file_path does not exist in project_root: {text}")
        return rel

    @staticmethod
    def _extract_diagnostics_list(result: object) -> list[dict[str, Any]]:
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if isinstance(result, dict):
            raw = result.get("diagnostics")
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
            return []
        diagnostics = getattr(result, "diagnostics", None)
        if isinstance(diagnostics, list):
            return [item for item in diagnostics if isinstance(item, dict)]
        return []

    @staticmethod
    def _severity_text(raw: object) -> str:
        if isinstance(raw, int):
            return {1: "error", 2: "warning", 3: "information", 4: "hint"}.get(raw, str(raw))
        return str(raw or "").strip().lower()

    @classmethod
    def _map_diagnostic_message(cls, item: dict[str, Any]) -> DiagnosticMessage:
        sev = cls._severity_text(item.get("severity"))
        line = 0
        col = 0
        rng = item.get("fullRange") or item.get("range")
        if isinstance(rng, dict):
            start = rng.get("start")
            if isinstance(start, dict):
                line = int(start.get("line", 0)) + 1
                col = int(start.get("character", 0)) + 1
        return DiagnosticMessage(
            severity=sev,
            message=str(item.get("message") or item.get("data") or ""),
            line=line,
            column=col,
        )

    @staticmethod
    def _extract_goals(goal_result: object) -> tuple[str, ...]:
        if isinstance(goal_result, dict):
            raw = goal_result.get("goals")
            if isinstance(raw, list):
                return tuple(str(item) for item in raw)
        return tuple()

    @staticmethod
    def _resolve_symbol_position(
        *,
        content: str,
        symbol: str,
        line: int | None,
        column: int | None,
    ) -> tuple[int, int] | None:
        lines = content.splitlines()
        if line is not None and column is not None:
            line0 = line - 1
            col0 = column - 1
            if line0 < 0 or line0 >= len(lines):
                return None
            if col0 < 0 or col0 > len(lines[line0]):
                return None
            return (line0, col0)

        for idx, text in enumerate(lines):
            pos = text.find(symbol)
            if pos != -1:
                return (idx, pos)
        return None

    @staticmethod
    def _uri_to_path(uri: str) -> Path | None:
        parsed = urlparse(uri)
        if parsed.scheme and parsed.scheme != "file":
            return None
        if parsed.scheme == "file":
            return Path(unquote(parsed.path))
        return Path(uri)

    @classmethod
    def _range_from_lsp(cls, raw: object) -> Range | None:
        if not isinstance(raw, dict):
            return None
        start = cls._position_from_lsp(raw.get("start"))
        end = cls._position_from_lsp(raw.get("end"))
        if start is None or end is None:
            return None
        return Range(start=start, end=end)

    @staticmethod
    def _position_from_lsp(raw: object) -> Position | None:
        if not isinstance(raw, dict):
            return None
        line = raw.get("line")
        char = raw.get("character", raw.get("column"))
        if not isinstance(line, int) or not isinstance(char, int):
            return None
        return Position(line=line + 1, column=char + 1)

    @staticmethod
    def _new_document_content_change(
        *,
        payload: str,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
    ):
        try:
            from leanclient import DocumentContentChange
            return DocumentContentChange(
                payload,
                [start_line, start_col],
                [end_line, end_col],
            )
        except Exception:
            # Fallback for test doubles that do not depend on leanclient runtime.
            @dataclass(slots=True)
            class _FallbackChange:
                text: str
                start: list[int]
                end: list[int]

            return _FallbackChange(
                text=payload,
                start=[start_line, start_col],
                end=[end_line, end_col],
            )

    @classmethod
    def _map_completion_items(cls, raw: object) -> list[CompletionItem]:
        out: list[CompletionItem] = []
        if not isinstance(raw, list):
            return out
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "")
            if not label:
                continue
            kind_raw = item.get("kind")
            kind = (
                _COMPLETION_KIND.get(kind_raw)
                if isinstance(kind_raw, int)
                else (str(kind_raw) if kind_raw is not None else None)
            )
            out.append(
                CompletionItem(
                    label=label,
                    kind=kind,
                    detail=(str(item["detail"]) if item.get("detail") is not None else None),
                )
            )
        return out

    @staticmethod
    def _sort_completion_items(
        *,
        content: str,
        line: int,
        column: int,
        items: list[CompletionItem],
    ) -> list[CompletionItem]:
        lines = content.splitlines()
        if line < 1 or line > len(lines):
            return sorted(items, key=lambda x: x.label.lower())
        text_before_cursor = lines[line - 1][: max(0, column - 1)] if column > 0 else ""
        prefix = ""
        if not text_before_cursor.endswith("."):
            prefix = re.split(r"[\s()\[\]{},:;.]+", text_before_cursor)[-1].lower()

        if not prefix:
            return sorted(items, key=lambda x: x.label.lower())

        def sort_key(item: CompletionItem) -> tuple[int, str]:
            label_lower = item.label.lower()
            if label_lower.startswith(prefix):
                return (0, label_lower)
            if prefix in label_lower:
                return (1, label_lower)
            return (2, label_lower)

        return sorted(items, key=sort_key)

    @classmethod
    def _parse_axiom_reports_from_diagnostics(
        cls,
        raw_diags: list[dict[str, Any]],
    ) -> dict[str, list[tuple[str, ...]]]:
        reports: dict[str, list[tuple[str, ...]]] = {}
        for item in raw_diags:
            if cls._severity_text(item.get("severity")) not in {"information", "info"}:
                continue
            msg = str(item.get("message") or item.get("data") or "")
            depends_match = _AXIOM_DEPENDS_RE.match(msg)
            if depends_match is not None:
                payload = depends_match.group("axioms").strip()
                reports.setdefault(depends_match.group("declaration"), []).append(
                    tuple(part.strip() for part in payload.split(",") if part.strip())
                )
                continue
            none_match = _AXIOM_NONE_RE.match(msg)
            if none_match is not None:
                reports.setdefault(none_match.group("declaration"), []).append(tuple())
        return reports

    @classmethod
    def _parse_compiled_declaration_reports(
        cls,
        raw_diags: list[dict[str, Any]],
    ) -> tuple[dict[int, dict[str, Any]], list[str]]:
        reports: dict[int, dict[str, Any]] = {}
        errors: list[str] = []
        for item in raw_diags:
            if cls._severity_text(item.get("severity")) not in {"information", "info"}:
                continue
            message = str(item.get("message") or item.get("data") or "")
            marker_index = message.find(_COMPILED_DECLARATION_MARKER)
            if marker_index < 0:
                continue
            payload = message[marker_index + len(_COMPILED_DECLARATION_MARKER) :].strip()
            try:
                report = json.loads(payload)
            except Exception as exc:
                errors.append(f"invalid compiled declaration report JSON: {exc}")
                continue
            if not isinstance(report, dict) or type(report.get("index")) is not int:
                errors.append("compiled declaration report is missing integer index")
                continue
            index = report["index"]
            if index in reports:
                errors.append(f"duplicate compiled declaration report index: {index}")
                continue
            reports[index] = report
        return reports, errors

    @staticmethod
    def _scan_source_warnings(abs_file: Path) -> tuple[SourceWarning, ...]:
        try:
            proc = subprocess.run(
                [
                    "rg",
                    "--json",
                    "--no-ignore",
                    "--no-messages",
                    _COMBINED_WARNING_PATTERN,
                    str(abs_file),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            return (SourceWarning(line=0, pattern="rg not installed"),)
        except subprocess.TimeoutExpired:
            return (SourceWarning(line=0, pattern="rg timeout"),)

        out: list[SourceWarning] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("type") != "match":
                continue
            data = event.get("data")
            if not isinstance(data, dict):
                continue
            text_obj = data.get("lines")
            if not isinstance(text_obj, dict):
                continue
            text = str(text_obj.get("text") or "").strip()
            line_number = int(data.get("line_number") or 0)
            for pattern in _WARNING_PATTERNS:
                m = re.search(pattern, text)
                if m is None:
                    continue
                out.append(SourceWarning(line=line_number, pattern=m.group(0)))
                break
        return tuple(out)
