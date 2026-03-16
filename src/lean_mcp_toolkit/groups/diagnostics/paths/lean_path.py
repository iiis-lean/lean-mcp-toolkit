"""Lean module path helper.

Canonical representation is Lean dot path, e.g. `Mathlib.Data.List.Basic`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_COMPONENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")


@dataclass(slots=True, frozen=True, order=True)
class LeanPath:
    dot: str

    def __post_init__(self) -> None:
        normalized = self.dot.strip().strip(".")
        if not normalized:
            raise ValueError("empty Lean path")
        parts = normalized.split(".")
        for part in parts:
            if not _COMPONENT_RE.match(part):
                raise ValueError(f"invalid Lean path component: {part!r}")
        object.__setattr__(self, "dot", ".".join(parts))

    @classmethod
    def from_dot(cls, value: str) -> "LeanPath":
        return cls(dot=value)

    @classmethod
    def from_rel_file(cls, rel_file: str) -> "LeanPath":
        rel = rel_file.strip()
        if rel.endswith(".lean"):
            rel = rel[: -len(".lean")]
        rel = rel.strip("/")
        if not rel:
            raise ValueError(f"invalid relative Lean file: {rel_file!r}")
        return cls(dot=rel.replace("/", "."))

    @classmethod
    def from_abs_file(cls, abs_file: Path, project_root: Path) -> "LeanPath":
        abs_norm = abs_file.resolve()
        root_norm = project_root.resolve()
        rel = abs_norm.relative_to(root_norm)
        return cls.from_rel_file(rel.as_posix())

    def to_rel_file(self) -> str:
        return self.dot.replace(".", "/") + ".lean"

    def to_abs_file(self, project_root: Path) -> Path:
        return project_root / self.to_rel_file()
