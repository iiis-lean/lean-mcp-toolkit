"""LeanExplore toolchain version mapping."""

from __future__ import annotations

LEAN_VERSION_TO_TOOLCHAIN_ID: dict[str, str] = {
    "4.28.0": "20260217_050001",
    "4.24.0": "v4.24.0",
}

TOOLCHAIN_BLACKLIST_NO_MATHLIB: set[str] = set()


def resolve_toolchain_id(lean_version: str) -> str:
    key = lean_version.strip()
    if not key:
        raise ValueError("mathlib lean version is empty")
    toolchain_id = LEAN_VERSION_TO_TOOLCHAIN_ID.get(key)
    if toolchain_id is None:
        raise ValueError(
            "unsupported mathlib lean version for lean_explore backend: "
            f"{lean_version}. Add mapping in LEAN_VERSION_TO_TOOLCHAIN_ID first."
        )
    if toolchain_id in TOOLCHAIN_BLACKLIST_NO_MATHLIB:
        raise ValueError(
            f"toolchain `{toolchain_id}` is blacklisted for missing Mathlib index"
        )
    return toolchain_id


__all__ = [
    "LEAN_VERSION_TO_TOOLCHAIN_ID",
    "TOOLCHAIN_BLACKLIST_NO_MATHLIB",
    "resolve_toolchain_id",
]
