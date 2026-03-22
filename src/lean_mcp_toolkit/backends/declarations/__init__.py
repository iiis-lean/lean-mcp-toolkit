"""Shared declaration extraction backends."""

from .base import DeclarationsBackend, DeclarationsBackendRequest, DeclarationsBackendResponse
from .lean_interact_backend import LeanInteractDeclarationsBackend
from .native_backend import NativeDeclarationsBackend

__all__ = [
    "DeclarationsBackend",
    "DeclarationsBackendRequest",
    "DeclarationsBackendResponse",
    "LeanInteractDeclarationsBackend",
    "NativeDeclarationsBackend",
]
