"""Compatibility shim for the old `native` declarations backend name."""

from __future__ import annotations

from .simple_lean_backend import SimpleLeanDeclarationsBackend


class NativeDeclarationsBackend(SimpleLeanDeclarationsBackend):
    """Backward-compatible alias for `simple_lean`."""

    backend_name = "native"


__all__ = ["NativeDeclarationsBackend"]
