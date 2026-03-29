"""Shared declaration extraction backends."""

from .base import DeclarationsBackend, DeclarationsBackendRequest, DeclarationsBackendResponse
from .lean_interact_backend import LeanInteractDeclarationsBackend
from .native_backend import NativeDeclarationsBackend
from .simple_lean_backend import SimpleLeanDeclarationsBackend

__all__ = [
    "DeclarationsBackend",
    "DeclarationsBackendRequest",
    "DeclarationsBackendResponse",
    "LeanInteractDeclarationsBackend",
    "NativeDeclarationsBackend",
    "SimpleLeanDeclarationsBackend",
]
