"""lsp_heavy service implementation.

This group adapts the heavier Lean LSP MCP tools and adds a toolkit-native
proof profiler built around ``lean --profile``.

Reference projects:
- lean-lsp-mcp (project-numina fork): https://github.com/project-numina/lean-lsp-mcp
- lean-lsp-mcp upstream: https://github.com/oOo0oOo/lean-lsp-mcp

Method mapping:
- ``run_widgets`` -> ``lean_get_widgets``
- ``run_widget_source`` -> ``lean_get_widget_source``
- ``run_proof_profile`` -> toolkit-native helper
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...backends.lean.path import LeanPath, resolve_project_root
from ...backends.lsp import LeanLSPClientManager
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...contracts.lsp_assist import Position, Range
from ...contracts.lsp_heavy import (
    LspProofProfileRequest,
    LspProofProfileResponse,
    LspWidgetSourceRequest,
    LspWidgetSourceResponse,
    LspWidgetsRequest,
    LspWidgetsResponse,
    WidgetInstance,
)
from ...core.services import LspHeavyService
from .profile_utils import profile_theorem


@dataclass(slots=True)
class LspHeavyServiceImpl(LspHeavyService):
    """Service adapter for widget-heavy and profiling LSP operations."""

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

    def run_widgets(self, req: LspWidgetsRequest) -> LspWidgetsResponse:
        """Adapt the upstream ``lean_get_widgets`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            raw_widgets = client.get_widgets(rel_path, req.line - 1, req.column - 1)
            items = tuple(self._map_widget(item) for item in self._widgets_list(raw_widgets))
            return LspWidgetsResponse(
                success=True,
                error_message=None,
                widgets=items,
                count=len(items),
            )
        except Exception as exc:
            return LspWidgetsResponse(
                success=False,
                error_message=str(exc),
                widgets=tuple(),
                count=0,
            )

    def run_widget_source(self, req: LspWidgetSourceRequest) -> LspWidgetSourceResponse:
        """Adapt the upstream ``lean_get_widget_source`` tool."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            javascript_hash = req.javascript_hash.strip()
            if not javascript_hash:
                raise ValueError("javascript_hash is required")
            client = self.lsp_client_manager.get_client(project_root)
            client.open_file(rel_path)
            raw_source = client.get_widget_source(
                rel_path,
                0,
                0,
                {"id": javascript_hash, "javascriptHash": javascript_hash},
            )
            if not isinstance(raw_source, dict):
                raise ValueError("widget source response must be a JSON object")
            source_text = raw_source.get("sourcetext")
            if source_text is not None:
                source_text = str(source_text)
                limit = self.config.lsp_heavy.widget_source_max_chars
                if limit is not None and limit > 0:
                    source_text = source_text[:limit]
            return LspWidgetSourceResponse(
                success=True,
                error_message=None,
                javascript_hash=javascript_hash,
                source_text=source_text,
                raw_source=dict(raw_source),
            )
        except Exception as exc:
            return LspWidgetSourceResponse(
                success=False,
                error_message=str(exc),
                javascript_hash=req.javascript_hash,
                source_text=None,
                raw_source=None,
            )

    def run_proof_profile(self, req: LspProofProfileRequest) -> LspProofProfileResponse:
        """Profile a theorem proof using the toolkit's ``lean --profile`` flow."""
        try:
            project_root = self._resolve_project_root(req.project_root)
            rel_path = self._normalize_file_path(project_root=project_root, file_path=req.file_path)
            top_n = (
                req.top_n
                if req.top_n is not None
                else self.config.lsp_heavy.proof_profile_default_top_n
            )
            timeout_seconds = (
                req.timeout_seconds
                if req.timeout_seconds is not None
                else self.config.lsp_heavy.proof_profile_default_timeout_seconds
            )
            if top_n <= 0:
                raise ValueError("top_n must be positive")
            if timeout_seconds is None or timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive")
            abs_path = (project_root / rel_path).resolve()
            profiled = profile_theorem(
                file_path=abs_path,
                theorem_line=req.line,
                project_root=project_root,
                timeout_seconds=timeout_seconds,
                top_n=top_n,
            )
            return LspProofProfileResponse(
                success=True,
                error_message=None,
                theorem_name=profiled.theorem_name,
                total_ms=profiled.total_ms,
                lines=profiled.lines,
                count=len(profiled.lines),
                categories=profiled.categories,
                category_count=len(profiled.categories),
            )
        except Exception as exc:
            return LspProofProfileResponse(
                success=False,
                error_message=str(exc),
                theorem_name=None,
                total_ms=None,
                lines=tuple(),
                count=0,
                categories=tuple(),
                category_count=0,
            )

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
    def _widgets_list(raw: object) -> list[JsonDict]:
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            payload = raw.get("widgets")
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
        return []

    @classmethod
    def _map_widget(cls, raw: JsonDict) -> WidgetInstance:
        name = raw.get("name")
        if name is None:
            name = raw.get("name?")
        return WidgetInstance(
            widget_id=str(raw.get("id") or ""),
            javascript_hash=(
                str(raw["javascriptHash"]) if raw.get("javascriptHash") is not None else None
            ),
            name=(str(name) if name is not None else None),
            range=cls._range_from_lsp(raw.get("range")),
            props=raw.get("props"),
            raw=dict(raw),
        )

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
