"""Normalize single declarations target into Lean dot path."""

from __future__ import annotations

from pathlib import Path

from ....backends.lean.path import LeanPath


def normalize_single_target_to_dot(*, project_root: Path, target: str) -> str:
    text = target.strip()
    if not text:
        raise ValueError("target is required")

    path_like = Path(text)
    if path_like.is_absolute():
        resolved = path_like.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"absolute target outside project_root: {target}") from exc
        if not resolved.is_file() or resolved.suffix != ".lean":
            raise ValueError(f"target must be a .lean file: {target}")
        return LeanPath.from_abs_file(resolved, project_root).dot

    if text.endswith(".lean"):
        module = LeanPath.from_rel_file(path_like.as_posix().strip("/"))
        abs_file = module.to_abs_file(project_root)
        if not abs_file.exists() or not abs_file.is_file():
            raise ValueError(f"target file does not exist: {target}")
        return module.dot

    candidate = (project_root / path_like).resolve()
    if candidate.exists():
        if candidate.is_dir():
            raise ValueError("directory target is not supported for declarations.extract")
        if candidate.is_file() and candidate.suffix == ".lean":
            return LeanPath.from_abs_file(candidate, project_root).dot
        raise ValueError(f"target must be a .lean file: {target}")

    module = LeanPath.from_dot(text)
    abs_file = module.to_abs_file(project_root)
    if not abs_file.exists() or not abs_file.is_file():
        raise ValueError(f"dot target does not exist in project_root: {target}")
    return module.dot
