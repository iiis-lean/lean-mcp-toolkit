"""Declarations service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from ...backends.declarations import DeclarationsBackend
from ...backends.lean.path import LeanPath, resolve_project_root
from ...backends.lsp import LeanLSPClientManager
from ...config import ToolkitConfig
from ...contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationItem,
    DeclarationLocateRange,
    DeclarationLocateRequest,
    DeclarationLocateResponse,
    DeclarationPosition,
)
from ...core.services import DeclarationsService
from ...interfaces.declarations import (
    DeclarationsInterfaceManager,
    DeclarationsInterfaceRequest,
)
from ...interfaces.declarations.backends import (
    LeanInteractDeclarationsInterfaceBackend,
    SimpleLeanDeclarationsInterfaceBackend,
    TextAstDeclarationsInterfaceBackend,
)
from ...tool_audit import audit_stage, get_current_audit_recorder
from .paths import normalize_single_target_to_dot


@dataclass(slots=True)
class DeclarationsServiceImpl(DeclarationsService):
    """Default declarations service implementation."""

    config: ToolkitConfig
    interface_manager: DeclarationsInterfaceManager
    lsp_client_manager: LeanLSPClientManager

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        backends: dict[str, DeclarationsBackend] | None = None,
        interface_manager: DeclarationsInterfaceManager | None = None,
        lsp_client_manager: LeanLSPClientManager | None = None,
    ):
        self.config = config
        self.interface_manager = interface_manager or DeclarationsInterfaceManager(
            config=config,
            backends=self._build_interface_backends(backends),
        )
        self.lsp_client_manager = lsp_client_manager or LeanLSPClientManager(
            backend_config=config.backends.lsp
        )

    def extract(self, req: DeclarationExtractRequest) -> DeclarationExtractResponse:
        try:
            with audit_stage("resolve_target"):
                project_root = self._resolve_project_root(req.project_root)
                target_dot = normalize_single_target_to_dot(
                    project_root=project_root,
                    target=req.target,
                )
                recorder = get_current_audit_recorder()
                if recorder is not None:
                    recorder.set_attr("target_dot", target_dot)
        except Exception as exc:
            return DeclarationExtractResponse(
                success=False,
                error_message=str(exc),
                total_declarations=0,
                declarations=tuple(),
            )

        interface_req = DeclarationsInterfaceRequest(
            project_root=project_root,
            target_dot=target_dot,
            timeout_seconds=self.config.declarations.default_timeout_seconds,
        )
        with audit_stage(
            "backend_extract",
            attrs={"backend": self.config.declarations.default_backend},
        ):
            interface_resp = self.interface_manager.extract(interface_req)
        return DeclarationExtractResponse(
            success=interface_resp.success,
            error_message=interface_resp.error_message,
            total_declarations=len(interface_resp.declarations),
            declarations=interface_resp.declarations,
        )

    def locate(self, req: DeclarationLocateRequest) -> DeclarationLocateResponse:
        try:
            with audit_stage("resolve_target"):
                project_root = self._resolve_project_root(req.project_root)
                source_dot = normalize_single_target_to_dot(
                    project_root=project_root,
                    target=req.source_file,
                )
                source_rel = LeanPath.from_dot(source_dot).to_rel_file()
        except Exception as exc:
            return DeclarationLocateResponse(
                success=False,
                error_message=str(exc),
            )

        if not req.symbol.strip():
            return DeclarationLocateResponse(
                success=False,
                error_message="symbol is required",
            )
        if (req.line is None) ^ (req.column is None):
            return DeclarationLocateResponse(
                success=False,
                error_message="line and column must be provided together",
            )

        try:
            with audit_stage("client_acquire"):
                client = self.lsp_client_manager.get_client(project_root)
                client.open_file(source_rel)
                source_content = client.get_file_content(source_rel)
        except Exception as exc:
            return DeclarationLocateResponse(
                success=False,
                error_message=f"failed to initialize LSP for source file: {exc}",
            )

        source_lines = source_content.splitlines()
        source_pos = self._resolve_source_pos(
            lines=source_lines,
            symbol=req.symbol,
            line=req.line,
            column=req.column,
        )
        if source_pos is None:
            return DeclarationLocateResponse(
                success=False,
                error_message=f"symbol `{req.symbol}` not found in source file",
            )

        line0, col0 = source_pos
        try:
            with audit_stage("request_lsp"):
                candidates = client.get_declarations(source_rel, line0, col0)
                if not candidates:
                    candidates = client.get_definitions(source_rel, line0, col0)
        except Exception as exc:
            return DeclarationLocateResponse(
                success=False,
                error_message=f"LSP declaration lookup failed: {exc}",
                source_pos=DeclarationPosition(line=line0, column=col0),
            )

        if not candidates:
            return DeclarationLocateResponse(
                success=False,
                error_message=f"no declaration target found for symbol `{req.symbol}`",
                source_pos=DeclarationPosition(line=line0, column=col0),
            )

        candidate = candidates[0]
        uri = candidate.get("targetUri") or candidate.get("uri")
        if not isinstance(uri, str) or not uri:
            return DeclarationLocateResponse(
                success=False,
                error_message="LSP response missing target uri",
                source_pos=DeclarationPosition(line=line0, column=col0),
            )

        target_path = self._uri_to_path(uri)
        if target_path is None:
            return DeclarationLocateResponse(
                success=False,
                error_message=f"unsupported target uri: {uri}",
                source_pos=DeclarationPosition(line=line0, column=col0),
            )
        target_abs = target_path.resolve()

        target_range_raw = (
            candidate.get("targetRange")
            or candidate.get("range")
            or candidate.get("targetSelectionRange")
        )
        target_range = self._range_from_lsp(target_range_raw)

        with audit_stage("match_declaration"):
            matched_decl = self._match_declaration_from_target(
                project_root=project_root,
                target_abs=target_abs,
                candidate=candidate,
            )

        return DeclarationLocateResponse(
            success=True,
            error_message=None,
            source_pos=DeclarationPosition(line=line0, column=col0),
            target_file_path=str(target_abs),
            target_range=target_range,
            matched_declaration=matched_decl,
        )

    def _resolve_project_root(self, project_root: str | None) -> Path:
        return resolve_project_root(
            project_root,
            default_project_root=self.config.server.default_project_root,
            allow_cwd_fallback=True,
        )

    def _build_interface_backends(
        self,
        backends: dict[str, DeclarationsBackend] | None,
    ) -> dict[str, object] | None:
        if backends is None:
            return None
        mapped: dict[str, object] = {
            "text_ast": TextAstDeclarationsInterfaceBackend(
                include_value=self.config.declarations.default_include_value
            ),
            "simple_lean": SimpleLeanDeclarationsInterfaceBackend(),
        }
        lean_interact = backends.get("lean_interact")
        if lean_interact is not None:
            mapped["lean_interact"] = LeanInteractDeclarationsInterfaceBackend(
                backend=lean_interact,
                include_value=self.config.declarations.default_include_value,
            )
        return mapped

    @staticmethod
    def _resolve_source_pos(
        *,
        lines: list[str],
        symbol: str,
        line: int | None,
        column: int | None,
    ) -> tuple[int, int] | None:
        if line is not None and column is not None:
            if line < 0 or line >= len(lines):
                return None
            text = lines[line]
            if column < 0 or column > len(text):
                return None
            return (line, column)

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
    def _range_from_lsp(cls, raw: object) -> DeclarationLocateRange | None:
        if not isinstance(raw, dict):
            return None
        start = raw.get("start")
        end = raw.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None
        start_pos = cls._position_from_lsp(start)
        end_pos = cls._position_from_lsp(end)
        if start_pos is None or end_pos is None:
            return None
        return DeclarationLocateRange(start=start_pos, end=end_pos)

    @staticmethod
    def _position_from_lsp(raw: object) -> DeclarationPosition | None:
        if not isinstance(raw, dict):
            return None
        line = raw.get("line")
        character = raw.get("character", raw.get("column"))
        if not isinstance(line, int) or not isinstance(character, int):
            return None
        return DeclarationPosition(line=line, column=character)

    def _match_declaration_from_target(
        self,
        *,
        project_root: Path,
        target_abs: Path,
        candidate: dict,
    ) -> DeclarationItem | None:
        try:
            target_dot = LeanPath.from_abs_file(target_abs, project_root).dot
        except Exception:
            return None

        extracted = self.extract(
            DeclarationExtractRequest(
                project_root=str(project_root),
                target=target_dot,
            )
        )
        if not extracted.success or not extracted.declarations:
            return None

        point = self._extract_target_point(candidate)
        if point is None:
            return None
        line0, col0 = point

        matches: list[tuple[int, DeclarationItem]] = []
        for decl in extracted.declarations:
            if not decl.decl_start_pos or not decl.decl_end_pos:
                continue
            if self._contains_point(
                start=decl.decl_start_pos,
                end=decl.decl_end_pos,
                line0=line0,
                col0=col0,
            ):
                span = self._span_size(decl.decl_start_pos, decl.decl_end_pos)
                matches.append((span, decl))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    @classmethod
    def _extract_target_point(cls, candidate: dict) -> tuple[int, int] | None:
        for key in ("targetSelectionRange", "targetRange", "range"):
            raw = candidate.get(key)
            if not isinstance(raw, dict):
                continue
            start = raw.get("start")
            pos = cls._position_from_lsp(start)
            if pos is not None:
                return (pos.line, pos.column)
        return None

    @staticmethod
    def _contains_point(
        *,
        start: DeclarationPosition,
        end: DeclarationPosition,
        line0: int,
        col0: int,
    ) -> bool:
        # DeclarationItem positions follow LeanInteract convention:
        # line is 1-based, column is 0-based, end is exclusive.
        sl = start.line - 1
        el = end.line - 1
        sc = start.column
        ec = end.column
        if sl < 0 or el < 0:
            return False
        if line0 < sl or line0 > el:
            return False
        if sl == el:
            return line0 == sl and sc <= col0 < ec
        if line0 == sl:
            return col0 >= sc
        if line0 == el:
            return col0 < ec
        return True

    @staticmethod
    def _span_size(start: DeclarationPosition, end: DeclarationPosition) -> int:
        line_span = max(0, end.line - start.line)
        return line_span * 1_000_000 + max(0, end.column - start.column)
