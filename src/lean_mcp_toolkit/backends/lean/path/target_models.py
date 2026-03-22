"""Target resolution models for diagnostics group."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lean_path import LeanPath


@dataclass(slots=True, frozen=True)
class ResolvedTargets:
    project_root_abs: Path
    modules: tuple[LeanPath, ...]

    def module_dots(self) -> tuple[str, ...]:
        return tuple(module.dot for module in self.modules)

    def module_rel_files(self) -> tuple[str, ...]:
        return tuple(module.to_rel_file() for module in self.modules)
