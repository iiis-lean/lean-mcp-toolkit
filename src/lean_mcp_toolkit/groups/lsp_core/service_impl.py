"""lsp_core service implementation.

This group adapts the core tool surface from the Lean LSP MCP ecosystem into
the toolkit's local/http/MCP architecture.

Reference projects:
- lean-lsp-mcp (project-numina fork): https://github.com/project-numina/lean-lsp-mcp
- lean-lsp-mcp upstream: https://github.com/oOo0oOo/lean-lsp-mcp

Method mapping:
- ``run_file_outline`` -> ``lean_file_outline``
- ``run_goal`` -> ``lean_goal``
- ``run_term_goal`` -> ``lean_term_goal``
- ``run_hover`` -> ``lean_hover_info``
- ``run_code_actions`` -> ``lean_code_actions``
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from ...backends.lsp import LeanLSPClientManager
from ...backends.lean.path import LeanPath
from ...config import ToolkitConfig
from ...contracts.lsp_core import (
    CodeAction,
    CodeActionEdit,
    DiagnosticMessage,
    LspCodeActionsRequest,
    LspCodeActionsResponse,
    LspFileOutlineRequest,
    LspFileOutlineResponse,
    LspGoalRequest,
    LspGoalResponse,
    LspHoverRequest,
    LspHoverResponse,
    LspTermGoalRequest,
    LspTermGoalResponse,
    MarkdownResponse,
    OutlineEntry,
    normalize_response_format,
)
from ...core.services import LspCoreService
from .renderers.markdown import (
    render_code_actions_markdown,
    render_file_outline_markdown,
    render_goal_markdown,
    render_hover_markdown,
    render_term_goal_markdown,
)


@dataclass(slots=True)
class LspCoreServiceImpl(LspCoreService):
    """Service adapter for core Lean LSP queries."""

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

    def run_file_outline(
        self,
        req: LspFileOutlineRequest,
    ) -> LspFileOutlineResponse | MarkdownResponse:
        """Adapt the upstream ``lean_file_outline`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(
                project_root=project_root,
                file_path=req.file_path,
            )
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            symbols = client.get_document_symbols(rel_path) or []

            imports = self._extract_imports(content)
            declarations = tuple(self._map_outline_entry(item) for item in symbols)

            max_declarations = (
                req.max_declarations
                if req.max_declarations is not None
                else self.config.lsp_core.default_max_declarations
            )
            total_declarations: int | None = None
            if max_declarations is not None and max_declarations > 0:
                if len(declarations) > max_declarations:
                    total_declarations = len(declarations)
                    declarations = declarations[:max_declarations]

            structured = LspFileOutlineResponse(
                success=True,
                error_message=None,
                imports=imports,
                declarations=declarations,
                total_declarations=total_declarations,
            )
            return self._project_response(
                req.response_format,
                render_file_outline_markdown(structured),
                structured,
            )
        except Exception as exc:
            structured = LspFileOutlineResponse(
                success=False,
                error_message=str(exc),
                imports=tuple(),
                declarations=tuple(),
                total_declarations=None,
            )
            return self._project_response(
                req.response_format,
                render_file_outline_markdown(structured),
                structured,
            )

    def run_goal(self, req: LspGoalRequest) -> LspGoalResponse | MarkdownResponse:
        """Adapt the upstream ``lean_goal`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(
                project_root=project_root,
                file_path=req.file_path,
            )
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            lines = content.splitlines()

            line_context = self._line_context(lines, req.line)

            if req.column is None:
                start_col = next((idx for idx, c in enumerate(line_context) if not c.isspace()), 0)
                end_col = len(line_context)
                goals_before = self._extract_goals(
                    client.get_goal(rel_path, req.line - 1, start_col)
                )
                goals_after = self._extract_goals(
                    client.get_goal(rel_path, req.line - 1, end_col)
                )
                structured = LspGoalResponse(
                    success=True,
                    error_message=None,
                    line_context=line_context,
                    goals=None,
                    goals_before=goals_before,
                    goals_after=goals_after,
                )
            else:
                self._validate_column(line_context, req.column)
                goals = self._extract_goals(
                    client.get_goal(rel_path, req.line - 1, req.column - 1)
                )
                structured = LspGoalResponse(
                    success=True,
                    error_message=None,
                    line_context=line_context,
                    goals=goals,
                    goals_before=None,
                    goals_after=None,
                )

            return self._project_response(
                req.response_format,
                render_goal_markdown(structured),
                structured,
            )
        except Exception as exc:
            structured = LspGoalResponse(
                success=False,
                error_message=str(exc),
                line_context=None,
                goals=None,
                goals_before=None,
                goals_after=None,
            )
            return self._project_response(
                req.response_format,
                render_goal_markdown(structured),
                structured,
            )

    def run_term_goal(
        self,
        req: LspTermGoalRequest,
    ) -> LspTermGoalResponse | MarkdownResponse:
        """Adapt the upstream ``lean_term_goal`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(
                project_root=project_root,
                file_path=req.file_path,
            )
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            lines = content.splitlines()

            line_context = self._line_context(lines, req.line)
            column = req.column if req.column is not None else max(1, len(line_context))
            self._validate_column(line_context, column)

            term_goal = client.get_term_goal(rel_path, req.line - 1, column - 1)
            expected_type = self._extract_term_goal(term_goal)
            structured = LspTermGoalResponse(
                success=True,
                error_message=None,
                line_context=line_context,
                expected_type=expected_type,
            )
            return self._project_response(
                req.response_format,
                render_term_goal_markdown(structured),
                structured,
            )
        except Exception as exc:
            structured = LspTermGoalResponse(
                success=False,
                error_message=str(exc),
                line_context=None,
                expected_type=None,
            )
            return self._project_response(
                req.response_format,
                render_term_goal_markdown(structured),
                structured,
            )

    def run_hover(self, req: LspHoverRequest) -> LspHoverResponse | MarkdownResponse:
        """Adapt the upstream ``lean_hover_info`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(
                project_root=project_root,
                file_path=req.file_path,
            )
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            lines = content.splitlines()
            line_context = self._line_context(lines, req.line)
            self._validate_column(line_context, req.column)

            hover = client.get_hover(rel_path, req.line - 1, req.column - 1)
            if hover is None:
                raise ValueError(
                    f"no hover information at line {req.line}, column {req.column}"
                )

            symbol = self._extract_symbol_from_hover(content, hover)
            info = self._extract_hover_info(hover)

            include_diagnostics = (
                req.include_diagnostics
                if req.include_diagnostics is not None
                else self.config.lsp_core.hover_include_diagnostics_default
            )
            diagnostics: tuple[DiagnosticMessage, ...] = tuple()
            if include_diagnostics:
                diagnostics = self._collect_hover_diagnostics(
                    client=client,
                    rel_path=rel_path,
                    line=req.line,
                    column=req.column,
                )

            structured = LspHoverResponse(
                success=True,
                error_message=None,
                symbol=symbol,
                info=info,
                diagnostics=diagnostics,
            )
            return self._project_response(
                req.response_format,
                render_hover_markdown(structured),
                structured,
            )
        except Exception as exc:
            structured = LspHoverResponse(
                success=False,
                error_message=str(exc),
                symbol=None,
                info=None,
                diagnostics=tuple(),
            )
            return self._project_response(
                req.response_format,
                render_hover_markdown(structured),
                structured,
            )

    def run_code_actions(
        self,
        req: LspCodeActionsRequest,
    ) -> LspCodeActionsResponse | MarkdownResponse:
        """Adapt the upstream ``lean_code_actions`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(
                project_root=project_root,
                file_path=req.file_path,
            )
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            content = client.get_file_content(rel_path)
            lines = content.splitlines()
            _ = self._line_context(lines, req.line)

            diagnostics_result = client.get_diagnostics(
                rel_path,
                start_line=req.line - 1,
                end_line=req.line - 1,
                inactivity_timeout=float(self.config.backends.lsp.diagnostics_timeout_seconds),
            )
            diagnostics = self._extract_diagnostics_list(diagnostics_result)

            seen_titles: set[str] = set()
            raw_actions: list[dict[str, Any]] = []
            for diag in diagnostics:
                diag_range = self._extract_diagnostic_range(diag)
                if diag_range is None:
                    continue
                start, end = diag_range
                actions = client.get_code_actions(
                    rel_path,
                    start[0],
                    start[1],
                    end[0],
                    end[1],
                )
                for action in actions or []:
                    if not isinstance(action, dict):
                        continue
                    title = str(action.get("title") or "")
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    raw_actions.append(action)

            parsed_actions = [
                self._resolve_code_action(client=client, action=item)
                for item in raw_actions
            ]
            parsed_actions = [item for item in parsed_actions if item is not None]

            max_actions = self.config.lsp_core.code_actions_max_actions
            if max_actions is not None and max_actions > 0:
                parsed_actions = parsed_actions[:max_actions]

            structured = LspCodeActionsResponse(
                success=True,
                error_message=None,
                actions=tuple(parsed_actions),
            )
            return self._project_response(
                req.response_format,
                render_code_actions_markdown(structured),
                structured,
            )
        except Exception as exc:
            structured = LspCodeActionsResponse(
                success=False,
                error_message=str(exc),
                actions=tuple(),
            )
            return self._project_response(
                req.response_format,
                render_code_actions_markdown(structured),
                structured,
            )

    def _resolve_project_root(self, project_root: str | None) -> Path:
        root = project_root or self.config.server.default_project_root or os.getcwd()
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"project_root is not a directory: {resolved}")
        return resolved

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
    def _extract_imports(content: str) -> tuple[str, ...]:
        imports: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("public import "):
                imports.append(stripped[14:].strip())
            elif stripped.startswith("import "):
                imports.append(stripped[7:].strip())
        return tuple(imports)

    @classmethod
    def _map_outline_entry(cls, item: object) -> OutlineEntry:
        if not isinstance(item, dict):
            return OutlineEntry(name="", kind="unknown", start_line=0, end_line=0)

        name = str(item.get("name") or "")
        kind = str(item.get("kind") or "unknown")
        start_line, end_line = cls._symbol_range(item.get("range"))
        type_signature = (
            str(item.get("detail"))
            if item.get("detail") is not None
            else None
        )

        children: list[OutlineEntry] = []
        raw_children = item.get("children")
        if isinstance(raw_children, list):
            for child in raw_children:
                children.append(cls._map_outline_entry(child))

        return OutlineEntry(
            name=name,
            kind=kind,
            start_line=start_line,
            end_line=end_line,
            type_signature=type_signature,
            children=tuple(children),
        )

    @staticmethod
    def _symbol_range(raw: object) -> tuple[int, int]:
        if not isinstance(raw, dict):
            return (0, 0)
        start = raw.get("start")
        end = raw.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return (0, 0)
        start_line = int(start.get("line") or 0) + 1
        end_line = int(end.get("line") or 0) + 1
        return (start_line, end_line)

    @staticmethod
    def _line_context(lines: list[str], line: int) -> str:
        if line < 1 or line > len(lines):
            raise ValueError(f"line {line} out of range (file has {len(lines)} lines)")
        return lines[line - 1]

    @staticmethod
    def _validate_column(line_context: str, column: int) -> None:
        max_column = len(line_context) + 1
        if column < 1 or column > max_column:
            raise ValueError(
                f"column {column} out of range (line has {len(line_context)} characters)"
            )

    @classmethod
    def _extract_goals(cls, raw_goal: object) -> tuple[str, ...]:
        if raw_goal is None:
            return tuple()
        if not isinstance(raw_goal, dict):
            return tuple()

        raw_goals = raw_goal.get("goals")
        if isinstance(raw_goals, list):
            return tuple(str(item) for item in raw_goals)

        rendered = raw_goal.get("rendered")
        if isinstance(rendered, str):
            text = cls._strip_fenced_block(rendered)
            text = text.strip()
            if text.lower() == "no goals" or not text:
                return tuple()
            return (text,)
        return tuple()

    @classmethod
    def _extract_term_goal(cls, raw_term_goal: object) -> str | None:
        if raw_term_goal is None or not isinstance(raw_term_goal, dict):
            return None
        goal = raw_term_goal.get("goal")
        if not isinstance(goal, str):
            return None
        return cls._strip_fenced_block(goal).strip() or None

    @classmethod
    def _extract_symbol_from_hover(cls, content: str, hover: dict[str, Any]) -> str | None:
        extracted = cls._extract_range_content(content, hover.get("range"))
        return extracted if extracted else None

    @staticmethod
    def _extract_hover_info(hover: dict[str, Any]) -> str | None:
        contents = hover.get("contents")
        if isinstance(contents, dict):
            value = contents.get("value")
            if isinstance(value, str):
                return value.replace("```lean\n", "").replace("\n```", "").strip()
        if isinstance(contents, str):
            return contents.strip()
        if isinstance(contents, list):
            texts: list[str] = []
            for item in contents:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("value"), str):
                    texts.append(str(item.get("value")))
            joined = "\n".join(texts).strip()
            return joined or None
        return None

    def _collect_hover_diagnostics(
        self,
        *,
        client: Any,
        rel_path: str,
        line: int,
        column: int,
    ) -> tuple[DiagnosticMessage, ...]:
        result = client.get_diagnostics(
            rel_path,
            start_line=line - 1,
            end_line=line - 1,
            inactivity_timeout=float(self.config.backends.lsp.diagnostics_timeout_seconds),
        )
        diagnostics = self._extract_diagnostics_list(result)
        out: list[DiagnosticMessage] = []
        for diag in diagnostics:
            if not isinstance(diag, dict):
                continue
            if not self._diag_contains_position(diag, line0=line - 1, col0=column - 1):
                continue
            out.append(self._map_diagnostic(diag))
        return tuple(out)

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
    def _extract_diagnostic_range(diag: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]] | None:
        raw = diag.get("fullRange") or diag.get("range")
        if not isinstance(raw, dict):
            return None
        start = raw.get("start")
        end = raw.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None
        if "line" not in start or "character" not in start:
            return None
        if "line" not in end or "character" not in end:
            return None
        return (
            (int(start["line"]), int(start["character"])),
            (int(end["line"]), int(end["character"])),
        )

    @classmethod
    def _diag_contains_position(cls, diag: dict[str, Any], *, line0: int, col0: int) -> bool:
        range_data = cls._extract_diagnostic_range(diag)
        if range_data is None:
            return False
        (start_line, start_col), (end_line, end_col) = range_data

        if line0 < start_line or line0 > end_line:
            return False
        if start_line == end_line:
            return start_col <= col0 <= end_col
        if line0 == start_line:
            return col0 >= start_col
        if line0 == end_line:
            return col0 <= end_col
        return True

    @classmethod
    def _map_diagnostic(cls, diag: dict[str, Any]) -> DiagnosticMessage:
        severity = diag.get("severity")
        if isinstance(severity, int):
            severity_map = {
                1: "error",
                2: "warning",
                3: "information",
                4: "hint",
            }
            severity_str = severity_map.get(severity, str(severity))
        else:
            severity_str = str(severity or "")

        line = 0
        column = 0
        diag_range = cls._extract_diagnostic_range(diag)
        if diag_range is not None:
            (start_line, start_col), _ = diag_range
            line = start_line + 1
            column = start_col + 1

        message = str(diag.get("message") or diag.get("data") or "")
        return DiagnosticMessage(
            severity=severity_str,
            message=message,
            line=line,
            column=column,
        )

    @classmethod
    def _resolve_code_action(cls, *, client: Any, action: dict[str, Any]) -> CodeAction | None:
        title = str(action.get("title") or "")
        if not title:
            return None

        resolved = action
        if "edit" not in resolved:
            try:
                resolved = client.get_code_action_resolve(action)
            except Exception:
                resolved = action

        if not isinstance(resolved, dict):
            return None
        if "error" in resolved:
            return None

        edits = cls._extract_code_action_edits(resolved.get("edit"))
        return CodeAction(
            title=title,
            is_preferred=bool(action.get("isPreferred", False)),
            edits=tuple(edits),
        )

    @staticmethod
    def _extract_code_action_edits(raw_edit: object) -> list[CodeActionEdit]:
        out: list[CodeActionEdit] = []
        if not isinstance(raw_edit, dict):
            return out

        raw_doc_changes = raw_edit.get("documentChanges")
        if isinstance(raw_doc_changes, list):
            for change in raw_doc_changes:
                if not isinstance(change, dict):
                    continue
                raw_edits = change.get("edits")
                if isinstance(raw_edits, list):
                    for edit in raw_edits:
                        parsed = _parse_single_edit(edit)
                        if parsed is not None:
                            out.append(parsed)

        raw_changes = raw_edit.get("changes")
        if isinstance(raw_changes, dict):
            for edits in raw_changes.values():
                if not isinstance(edits, list):
                    continue
                for edit in edits:
                    parsed = _parse_single_edit(edit)
                    if parsed is not None:
                        out.append(parsed)

        return out

    @staticmethod
    def _extract_range_content(content: str, raw_range: object) -> str | None:
        if not isinstance(raw_range, dict):
            return None
        start = raw_range.get("start")
        end = raw_range.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None

        try:
            start_line = int(start.get("line", -1))
            start_col = int(start.get("character", -1))
            end_line = int(end.get("line", -1))
            end_col = int(end.get("character", -1))
        except Exception:
            return None

        lines = content.splitlines()
        if start_line < 0 or end_line < start_line:
            return None
        if end_line >= len(lines):
            return None

        if start_line == end_line:
            line = lines[start_line]
            if start_col < 0 or end_col < start_col or end_col > len(line):
                return None
            return line[start_col:end_col]

        if start_col < 0 or start_col > len(lines[start_line]):
            return None
        if end_col < 0 or end_col > len(lines[end_line]):
            return None

        parts = [lines[start_line][start_col:]]
        for idx in range(start_line + 1, end_line):
            parts.append(lines[idx])
        parts.append(lines[end_line][:end_col])
        return "\n".join(parts)

    @staticmethod
    def _strip_fenced_block(text: str) -> str:
        value = text.strip()
        if value.startswith("```lean") and value.endswith("```"):
            value = value[len("```lean") : -len("```")]
        elif value.startswith("```") and value.endswith("```"):
            value = value[len("```") : -len("```")]
        return value.strip("\n")

    def _project_response(
        self,
        requested_format: str | None,
        markdown: str,
        structured: Any,
    ) -> Any:
        fmt = normalize_response_format(
            requested_format,
            default=self.config.lsp_core.default_response_format,
        )
        if fmt == "markdown":
            return MarkdownResponse(markdown=markdown)
        return structured


def _parse_single_edit(raw: object) -> CodeActionEdit | None:
    if not isinstance(raw, dict):
        return None
    raw_range = raw.get("range")
    if not isinstance(raw_range, dict):
        return None
    start = raw_range.get("start")
    end = raw_range.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None

    try:
        start_line = int(start.get("line", 0)) + 1
        start_col = int(start.get("character", 0)) + 1
        end_line = int(end.get("line", 0)) + 1
        end_col = int(end.get("character", 0)) + 1
    except Exception:
        return None

    return CodeActionEdit(
        new_text=str(raw.get("newText") or ""),
        start_line=start_line,
        start_column=start_col,
        end_line=end_line,
        end_column=end_col,
    )


__all__ = ["LspCoreServiceImpl"]
