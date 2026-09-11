"""Normalize a declarations target without conflating files and Lean modules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ....backends.lean.path import LeanPath


@dataclass(slots=True, frozen=True)
class NormalizedDeclarationTarget:
    """Canonical project-relative file and its optional Lean module identity."""

    relative_file: str
    module_dot: str | None


def normalize_single_target(*, project_root: Path, target: str) -> NormalizedDeclarationTarget:
    text = target.strip()
    if not text:
        raise ValueError("target is required")

    root = project_root.resolve()
    path_like = Path(text)
    if path_like.is_absolute():
        return _normalize_file_path(
            root=root,
            path=path_like,
            target=target,
            outside_message="absolute target outside project_root",
        )

    if text.endswith(".lean"):
        return _normalize_file_path(
            root=root,
            path=root / path_like,
            target=target,
            outside_message="relative target outside project_root",
        )

    candidate = root / path_like
    if candidate.exists():
        if candidate.is_dir():
            raise ValueError("directory target is not supported for declarations.extract")
        return _normalize_file_path(
            root=root,
            path=candidate,
            target=target,
            outside_message="relative target outside project_root",
        )

    module = LeanPath.from_dot(text)
    normalized = _normalize_file_path(
        root=root,
        path=root / module.to_rel_file(),
        target=target,
        outside_message="dot target outside project_root",
        missing_message="dot target does not exist in project_root",
    )
    return NormalizedDeclarationTarget(
        relative_file=normalized.relative_file,
        module_dot=module.dot,
    )


def _normalize_file_path(
    *,
    root: Path,
    path: Path,
    target: str,
    outside_message: str,
    missing_message: str = "target file does not exist",
) -> NormalizedDeclarationTarget:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{outside_message}: {target}") from exc
    if not resolved.exists():
        raise ValueError(f"{missing_message}: {target}")
    if not resolved.is_file() or resolved.suffix != ".lean":
        raise ValueError(f"target must be a .lean file: {target}")

    relative_file = relative.as_posix()
    return NormalizedDeclarationTarget(
        relative_file=relative_file,
        module_dot=_module_dot_for_relative_file(relative_file),
    )


def _module_dot_for_relative_file(relative_file: str) -> str | None:
    try:
        module = LeanPath.from_rel_file(relative_file)
    except ValueError:
        return None
    if module.to_rel_file() != relative_file:
        return None
    return module.dot


__all__ = ["NormalizedDeclarationTarget", "normalize_single_target"]
