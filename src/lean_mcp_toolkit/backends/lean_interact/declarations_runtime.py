"""Runtime wrapper for LeanInteract-based declaration extraction."""

from __future__ import annotations

from ..lean_interact_runtime import LeanInteractRuntimeManager


class LeanInteractDeclarationsRuntime(LeanInteractRuntimeManager):
    """Thin alias around the shared LeanInteract runtime manager."""


__all__ = ["LeanInteractDeclarationsRuntime"]
