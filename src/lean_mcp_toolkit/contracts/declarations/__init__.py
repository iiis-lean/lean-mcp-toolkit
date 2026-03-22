"""Contracts for declarations group."""

from .extract import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationItem,
    DeclarationPosition,
)
from .locate import (
    DeclarationLocateRange,
    DeclarationLocateRequest,
    DeclarationLocateResponse,
)

__all__ = [
    "DeclarationExtractRequest",
    "DeclarationExtractResponse",
    "DeclarationItem",
    "DeclarationPosition",
    "DeclarationLocateRequest",
    "DeclarationLocateRange",
    "DeclarationLocateResponse",
]
