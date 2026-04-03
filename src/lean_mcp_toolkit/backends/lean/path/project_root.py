"""Helpers for resolving Lean project roots from arbitrary in-project paths."""

from __future__ import annotations

import os
from pathlib import Path

_LEAN_PROJECT_MARKERS: tuple[str, ...] = (
    "lakefile.lean",
    "lakefile.toml",
    "lean-toolchain",
)
_LEAN_PROJECT_MARKER_DIRS: tuple[tuple[str, ...], ...] = (
    (".lake", "packages"),
    (".lake", "build"),
)


def resolve_project_root(
    raw_path: str | Path | None,
    *,
    default_project_root: str | Path | None = None,
    allow_cwd_fallback: bool = True,
) -> Path:
    """Resolve a Lean project root from a root or any path inside the project.

    Resolution order:
    1. explicit ``raw_path`` when provided
    2. configured ``default_project_root`` when provided
    3. current working directory when ``allow_cwd_fallback`` is true

    If the selected path is inside a Lean project, walk upward until a directory
    containing standard Lean project markers is found. If no marker is found,
    keep backward compatibility by returning the resolved directory itself (or
    the parent directory when a file path was provided).
    """

    base = _select_base_path(
        raw_path=raw_path,
        default_project_root=default_project_root,
        allow_cwd_fallback=allow_cwd_fallback,
    )
    search_start = base.parent if base.is_file() else base
    resolved = search_start.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"project_root is not a directory: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"project_root is not a directory: {resolved}")

    project_root = _discover_lean_project_root(resolved)
    return project_root if project_root is not None else resolved


def _select_base_path(
    *,
    raw_path: str | Path | None,
    default_project_root: str | Path | None,
    allow_cwd_fallback: bool,
) -> Path:
    if raw_path is not None and str(raw_path).strip():
        return Path(raw_path)
    if default_project_root is not None and str(default_project_root).strip():
        return Path(default_project_root)
    if allow_cwd_fallback:
        return Path(os.getcwd())
    raise ValueError("project_root is required")


def _discover_lean_project_root(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in _LEAN_PROJECT_MARKERS):
            return candidate
        if any((candidate.joinpath(*parts)).exists() for parts in _LEAN_PROJECT_MARKER_DIRS):
            return candidate
    return None


__all__ = ["resolve_project_root"]
