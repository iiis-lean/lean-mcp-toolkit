"""Declarations interface adapter for LeanInteract extraction.

This backend wraps the toolkit's LeanInteract runtime. It remains the semantic
reference for field meanings when text-level extraction is compared against it.
"""

from __future__ import annotations

from pathlib import Path

from ....backends.declarations import DeclarationsBackendRequest
from ....contracts.declarations import DeclarationItem
from ..base import DeclarationsInterfaceRequest, DeclarationsInterfaceResponse
from ..mappers import map_lean_raw_declarations_to_items


class LeanInteractDeclarationsInterfaceBackend:
    """Adapt LeanInteract extraction results to ``DeclarationsInterfaceResponse``.

    Compared with ``text_ast``:
    - names and kinds come from Lean-side extraction rather than syntax-only
      parsing;
    - signatures reflect LeanInteract's declaration view;
    - ranges are derived from Lean-side positions plus source slicing.
    """

    backend_name = "lean_interact"

    def __init__(
        self,
        *,
        backend: object,
        include_value: bool = False,
    ) -> None:
        self.backend = backend
        self.include_value = include_value

    def extract(self, req: DeclarationsInterfaceRequest) -> DeclarationsInterfaceResponse:
        backend_resp = self.backend.extract(self._to_backend_req(req))
        items = self._map_items(
            project_root=req.project_root,
            target_dot=req.target_dot,
            raw_declarations=backend_resp.declarations,
        )
        return DeclarationsInterfaceResponse(
            success=backend_resp.success,
            error_message=backend_resp.error_message,
            declarations=items,
        )

    def extract_batch(
        self,
        reqs: tuple[DeclarationsInterfaceRequest, ...],
    ) -> tuple[DeclarationsInterfaceResponse, ...]:
        backend_reqs = tuple(self._to_backend_req(req) for req in reqs)
        backend_resps = self.backend.extract_batch(backend_reqs)
        out: list[DeclarationsInterfaceResponse] = []
        for req, backend_resp in zip(reqs, backend_resps, strict=True):
            out.append(
                DeclarationsInterfaceResponse(
                    success=backend_resp.success,
                    error_message=backend_resp.error_message,
                    declarations=self._map_items(
                        project_root=req.project_root,
                        target_dot=req.target_dot,
                        raw_declarations=backend_resp.declarations,
                    ),
                )
            )
        return tuple(out)

    def _to_backend_req(self, req: DeclarationsInterfaceRequest) -> DeclarationsBackendRequest:
        return DeclarationsBackendRequest(
            project_root=req.project_root,
            target_dot=req.target_dot,
            timeout_seconds=req.timeout_seconds,
        )

    def _map_items(
        self,
        *,
        project_root: Path,
        target_dot: str,
        raw_declarations: tuple[object, ...],
    ) -> tuple[DeclarationItem, ...]:
        source_lines = self._load_source_lines(project_root=project_root, target_dot=target_dot)
        return map_lean_raw_declarations_to_items(
            raw_declarations,
            source_lines=source_lines,
            include_value=self.include_value,
        )

    @staticmethod
    def _load_source_lines(*, project_root: Path, target_dot: str) -> list[str] | None:
        from ....backends.lean.path import LeanPath

        source_file = project_root / LeanPath.from_dot(target_dot).to_rel_file()
        try:
            return source_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            return None


__all__ = ["LeanInteractDeclarationsInterfaceBackend"]
