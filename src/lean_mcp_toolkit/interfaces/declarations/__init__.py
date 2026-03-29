"""Unified declarations capability interface."""

from .base import DeclarationsInterfaceBackend, DeclarationsInterfaceRequest, DeclarationsInterfaceResponse
from .manager import DeclarationsInterfaceManager

__all__ = [
    "DeclarationsInterfaceBackend",
    "DeclarationsInterfaceManager",
    "DeclarationsInterfaceRequest",
    "DeclarationsInterfaceResponse",
]
