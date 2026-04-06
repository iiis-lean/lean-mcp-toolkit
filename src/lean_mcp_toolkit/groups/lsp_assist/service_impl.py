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
- ``run_theorem_soundness`` -> toolkit-native theorem soundness helper
"""

from __future__ import annotations

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
    CompletionItem,
    DiagnosticMessage,
    LspCompletionsRequest,
    LspCompletionsResponse,
    LspDeclarationFileRequest,
    LspDeclarationFileResponse,
    LspMultiAttemptRequest,
    LspMultiAttemptResponse,
    LspRunSnippetRequest,
    LspRunSnippetResponse,
    LspTheoremSoundnessRequest,
    LspTheoremSoundnessResponse,
    Position,
    Range,
    SourceWarning,
)
from ...core.services import LspAssistService

_AXIOM_DEPENDS_RE = re.compile(r"depends on axioms:\s*\[(?P<axioms>.*)\]")

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
            max_chars = max(1, self.config.lsp_assist.run_snippet_max_code_chars)
            if len(code) > max_chars:
                raise ValueError(f"code exceeds max length: {len(code)} > {max_chars}")

            rel_path = f"_mcp_snippet_{uuid.uuid4().hex}.lean"
            snippet_path = (project_root / rel_path).resolve()
            snippet_path.write_text(code, encoding="utf-8")

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)

            inactivity_timeout = float(self._resolve_run_snippet_timeout_seconds(req.timeout_seconds))
            raw_diag = client.get_diagnostics(
                rel_path,
                inactivity_timeout=inactivity_timeout,
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
            else self.config.lsp_assist.run_snippet_default_timeout_seconds
        )
        if timeout_seconds is None or timeout_seconds <= 0:
            timeout_seconds = self.config.backends.lsp.diagnostics_timeout_seconds

        max_timeout = max(1, int(self.config.lsp_assist.run_snippet_max_timeout_seconds))
        return min(max(1, int(timeout_seconds)), max_timeout)

    def run_theorem_soundness(
        self,
        req: LspTheoremSoundnessRequest,
    ) -> LspTheoremSoundnessResponse:
        """Check theorem soundness via a temporary ``#print axioms`` file."""
        verify_path: Path | None = None
        rel_path: str | None = None
        client: Any | None = None
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_file = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            theorem_name = req.theorem_name.strip()
            if not theorem_name:
                raise ValueError("theorem_name is required")

            module_dot = LeanPath.from_rel_file(rel_file).dot
            rel_path = f"_mcp_verify_{uuid.uuid4().hex}.lean"
            verify_path = (project_root / rel_path).resolve()
            verify_path.write_text(
                f"import {module_dot}\n#print axioms {theorem_name}\n",
                encoding="utf-8",
            )

            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            raw_diag = client.get_diagnostics(
                rel_path,
                inactivity_timeout=float(self.config.backends.lsp.diagnostics_timeout_seconds),
            )
            diagnostics = self._extract_diagnostics_list(raw_diag)
            error_messages = [
                str(item.get("message") or item.get("data") or "")
                for item in diagnostics
                if self._severity_text(item.get("severity")) == "error"
            ]
            if error_messages:
                return LspTheoremSoundnessResponse(
                    success=False,
                    error_message="; ".join(msg for msg in error_messages if msg.strip()),
                    axioms=tuple(),
                    warnings=tuple(),
                    axiom_count=0,
                    warning_count=0,
                )

            axioms = self._parse_axioms_from_diagnostics(diagnostics)
            scan_source = (
                req.scan_source
                if req.scan_source is not None
                else self.config.lsp_assist.theorem_soundness_scan_source_default
            )
            warnings = (
                self._scan_source_warnings((project_root / rel_file).resolve())
                if scan_source
                else tuple()
            )
            return LspTheoremSoundnessResponse(
                success=True,
                error_message=None,
                axioms=axioms,
                warnings=warnings,
                axiom_count=len(axioms),
                warning_count=len(warnings),
            )
        except Exception as exc:
            return LspTheoremSoundnessResponse(
                success=False,
                error_message=str(exc),
                axioms=tuple(),
                warnings=tuple(),
                axiom_count=0,
                warning_count=0,
            )
        finally:
            if client is not None and rel_path is not None:
                try:
                    client.close_files([rel_path])
                except Exception:
                    pass
            if verify_path is not None:
                try:
                    verify_path.unlink(missing_ok=True)
                except Exception:
                    pass

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

    @staticmethod
    def _parse_axioms_from_diagnostics(raw_diags: list[dict[str, Any]]) -> tuple[str, ...]:
        axioms: list[str] = []
        for item in raw_diags:
            if LspAssistServiceImpl._severity_text(item.get("severity")) not in {"information", "info"}:
                continue
            msg = str(item.get("message") or item.get("data") or "")
            match = _AXIOM_DEPENDS_RE.search(msg)
            if match is None:
                continue
            payload = match.group("axioms").strip()
            if not payload:
                continue
            axioms.extend(part.strip() for part in payload.split(",") if part.strip())
        return tuple(axioms)

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
