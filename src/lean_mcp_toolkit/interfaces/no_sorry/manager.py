"""Manager for ``no_sorry`` interface backends.

This keeps backend selection out of ``groups.diagnostics`` so the group can
focus on orchestration rather than on whether the check is implemented via Lean
diagnostics or the lightweight text/AST scanner.
"""

from __future__ import annotations

from collections.abc import Callable

from ...backends.lean.path import TargetResolver
from ...config import ToolkitConfig
from ...contracts.diagnostics import LintRequest, NoSorryResult
from .backends import LeanNoSorryInterfaceBackend, TextAstNoSorryInterfaceBackend
from .base import NoSorryInterfaceBackend


class NoSorryInterfaceManager:
    """Dispatch ``no_sorry`` to the configured implementation.

    Backend characteristics:
    - ``lean``: semantically closer to historical behavior, but heavier.
    - ``text_ast``: much faster; positions and messages are text-oriented rather
      than elaboration-oriented.
    """

    def __init__(
        self,
        *,
        config: ToolkitConfig,
        resolver: TargetResolver,
        lean_runner: Callable[[LintRequest], NoSorryResult],
        backends: dict[str, NoSorryInterfaceBackend] | None = None,
    ) -> None:
        self.config = config
        self.backends = backends or {
            "text_ast": TextAstNoSorryInterfaceBackend(config=config, resolver=resolver),
            "lean": LeanNoSorryInterfaceBackend(runner=lean_runner),
        }

    def run(self, req: LintRequest) -> NoSorryResult:
        backend = self.backends.get(self.config.diagnostics.no_sorry_backend)
        if backend is None:
            return NoSorryResult(
                check_id="no_sorry",
                success=False,
                message=f"unsupported no_sorry backend: {self.config.diagnostics.no_sorry_backend}",
                sorries=tuple(),
            )
        return backend.run(req)


__all__ = ["NoSorryInterfaceManager"]
