"""Contracts for declarations group."""

from .extract import (
    DeclarationExtractRequest,
    DeclarationExtractResponse,
    DeclarationItem,
    DeclarationPosition,
    DeclarationSourceDiagnostics,
    DeclarationUnrecognizedCommand,
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
    "DeclarationSourceDiagnostics",
    "DeclarationUnrecognizedCommand",
    "DeclarationLocateRequest",
    "DeclarationLocateRange",
    "DeclarationLocateResponse",
]
