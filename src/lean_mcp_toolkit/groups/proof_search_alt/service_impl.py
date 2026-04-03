"""proof_search_alt service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...backends.lean.path import LeanPath, resolve_project_root
from ...backends.lsp import LeanLSPClientManager
from ...backends.search_providers import ProofSearchAltBackendManager
from ...config import ToolkitConfig
from ...contracts.proof_search_alt import (
    HammerPremiseItem,
    ProofSearchAltHammerPremiseRequest,
    ProofSearchAltHammerPremiseResponse,
    ProofSearchAltStateSearchRequest,
    ProofSearchAltStateSearchResponse,
    StateSearchItem,
)
from ...core.services import ProofSearchAltService


@dataclass(slots=True)
class ProofSearchAltServiceImpl(ProofSearchAltService):
    config: ToolkitConfig
    lsp_client_manager: LeanLSPClientManager
    backend_manager: ProofSearchAltBackendManager

    def __init__(
        self,
        config: ToolkitConfig,
        *,
        lsp_client_manager: LeanLSPClientManager | None = None,
        backend_manager: ProofSearchAltBackendManager | None = None,
    ):
        self.config = config
        self.lsp_client_manager = lsp_client_manager or LeanLSPClientManager(
            backend_config=config.backends.lsp
        )
        self.backend_manager = backend_manager or ProofSearchAltBackendManager(
            config=config.backends.search_providers
        )

    def run_state_search(
        self,
        req: ProofSearchAltStateSearchRequest,
    ) -> ProofSearchAltStateSearchResponse:
        try:
            goal = self._extract_goal(
                project_root=req.project_root,
                file_path=req.file_path,
                line=req.line,
                column=req.column,
            )
            limit = self._cap(
                req.num_results or self.config.proof_search_alt.state_search_default_num_results,
                self.backend_manager.config.state_search.max_results_hard_limit,
            )
            items = tuple(
                StateSearchItem.from_dict(item)
                for item in self.backend_manager.state_search.search(
                    goal=goal,
                    num_results=limit,
                    include_raw_payload=self.config.proof_search_alt.include_raw_payload_default,
                )
            )
            return ProofSearchAltStateSearchResponse(
                success=True,
                error_message=None,
                provider="state_search",
                goal=goal,
                backend_mode="remote",
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return ProofSearchAltStateSearchResponse(
                success=False,
                error_message=str(exc),
                provider="state_search",
                goal=None,
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    def run_hammer_premise(
        self,
        req: ProofSearchAltHammerPremiseRequest,
    ) -> ProofSearchAltHammerPremiseResponse:
        try:
            goal = self._extract_goal(
                project_root=req.project_root,
                file_path=req.file_path,
                line=req.line,
                column=req.column,
            )
            limit = self._cap(
                req.num_results or self.config.proof_search_alt.hammer_premise_default_num_results,
                self.backend_manager.config.hammer_premise.max_results_hard_limit,
            )
            items = tuple(
                HammerPremiseItem.from_dict(item)
                for item in self.backend_manager.hammer_premise.search(
                    goal=goal,
                    num_results=limit,
                    include_raw_payload=self.config.proof_search_alt.include_raw_payload_default,
                )
            )
            return ProofSearchAltHammerPremiseResponse(
                success=True,
                error_message=None,
                provider="hammer_premise",
                goal=goal,
                backend_mode="remote",
                items=items,
                count=len(items),
            )
        except Exception as exc:
            return ProofSearchAltHammerPremiseResponse(
                success=False,
                error_message=str(exc),
                provider="hammer_premise",
                goal=None,
                backend_mode="remote",
                items=tuple(),
                count=0,
            )

    def _extract_goal(self, *, project_root: str | None, file_path: str, line: int, column: int) -> str:
        root = self._resolve_project_root(project_root)
        rel_path = self._normalize_file_path(project_root=root, file_path=file_path)
        client = self.lsp_client_manager.get_client(root)
        client.open_file(rel_path)
        goal = client.get_goal(rel_path, line - 1, column - 1)
        goals = goal.get("goals") if isinstance(goal, dict) else None
        if not isinstance(goals, list) or not goals:
            raise ValueError(f"no goals found at line {line}, column {column}")
        return str(goals[0])

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
        module = LeanPath.from_dot(text)
        rel = module.to_rel_file()
        abs_file = (root / rel).resolve()
        if not abs_file.exists() or not abs_file.is_file():
            raise ValueError(f"dot file_path does not exist in project_root: {text}")
        return rel

    @staticmethod
    def _cap(value: int, hard_limit: int) -> int:
        return max(1, min(value, hard_limit))
